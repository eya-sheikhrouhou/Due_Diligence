from huggingface_hub import login
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch
import os
import fitz  # PyMuPDF
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.feature_extraction.text import TfidfVectorizer

# 🔧 Prevent GPU Memory Issues
os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "expandable_segments:True"

# 🔐 Hugging Face Authentication
login("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")

# ✅ Load Optimized Model
model_name = "TheBloke/Mistral-7B-Instruct-v0.1-GPTQ"

# 🔥 Model Optimization (4-bit Quantization)
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True
)

# ✅ Load Tokenizer
tokenizer = AutoTokenizer.from_pretrained(model_name)

# ✅ Load Model with Optimized Memory
model = AutoModelForCausalLM.from_pretrained(
    model_name,
    device_map="auto",
    offload_buffers=True  # Reduce VRAM usage
)
model = torch.compile(model)  # 🚀 Speed up execution

print("✅ Mistral-7B-v0.1 Model Loaded!")

# 📂 Define PDF Directory
PDF_DIR = r"C:\Users\omarb\OneDrive\Bureau\PI\DATA\LOT1"

# 📂 Load and Extract Text from PDFs
def extract_text_from_pdfs():
    pdf_texts = {}
    pdf_files = [f for f in os.listdir(PDF_DIR) if f.endswith(".pdf")]

    for pdf in pdf_files:
        pdf_path = os.path.join(PDF_DIR, pdf)
        with fitz.open(pdf_path) as doc:
            text = "\n".join([page.get_text("text") for page in doc if page.get_text("text")])
            pdf_texts[pdf] = text  # Store by filename

    return pdf_texts

# 🚀 Load Documents
documents = extract_text_from_pdfs()
print(f"✅ Loaded {len(documents)} PDFs.")

# 🚀 Load Embedding Model
embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# 📌 TF-IDF: Select Most Relevant Document
def find_best_document(query, docs):
    if not docs:
        return None, ""

    vectorizer = TfidfVectorizer(stop_words="english")
    corpus = list(docs.values()) + [query]
    tfidf_matrix = vectorizer.fit_transform(corpus)

    # Compute similarity between query and all documents
    similarity_scores = (tfidf_matrix[-1] @ tfidf_matrix[:-1].T).toarray()[0]
    best_doc_idx = np.argmax(similarity_scores)

    # Return best matching document
    best_doc_name = list(docs.keys())[best_doc_idx]
    best_doc_text = docs[best_doc_name]

    return best_doc_name, best_doc_text

# 📌 FAISS: Create Index for the Best Document
def create_faiss_index(text):
    chunks = [text[i:i+256] for i in range(0, len(text), 256)]
    if not chunks:
        return None, []

    embeddings = np.array(embed_model.encode(chunks, convert_to_numpy=True))

    index = faiss.IndexFlatL2(embeddings.shape[1])
    index.add(embeddings)

    return index, chunks

# 🔎 Retrieve Most Relevant Chunk from FAISS
def retrieve_best_chunk(query, chunks, index):
    if not chunks or index is None:
        return "⚠ No relevant context found."

    query_embedding = embed_model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_embedding, 1)  # Get top 1 chunk

    return chunks[indices[0][0]] if len(indices[0]) > 0 else "⚠ No relevant context found."

# 🏆 Generate AI Response
def generate_rag_response(query, documents):
    best_doc_name, best_doc_text = find_best_document(query, documents)

    if not best_doc_name:
        return "⚠ No relevant document found."

    # Create FAISS index for the best document
    index, chunks = create_faiss_index(best_doc_text)
    
    # Retrieve best chunk
    retrieved_context = retrieve_best_chunk(query, chunks, index)

    # Ensure relevant text is available
    if not retrieved_context.strip():
        return "⚠ No relevant context found."

    # 🔹 Optimized Query
    full_query = f"""
    You are an AI assistant specializing in finance and legal entity identification.
    Your task is to analyze the extracted context from legal documents and provide an accurate response.

    --- Context ---
    {retrieved_context}

    --- Question ---
    {query}

    --- Answer ---
    """

    device = "cuda" if torch.cuda.is_available() else "cpu"
    inputs = tokenizer(full_query, return_tensors="pt", truncation=True, max_length=512).to(device)

    # 🔥 Faster Response Generation
    try:
        with torch.no_grad():
            output = model.generate(**inputs, max_new_tokens=30, num_beams=1, do_sample=False)
        response = tokenizer.decode(output[0], skip_special_tokens=True)
    except torch.cuda.OutOfMemoryError:
        response = "⚠ GPU memory insufficient. Try reducing token limit."

    print(f"\n📜 **Best Document:** {best_doc_name}")
    print(f"\n🔍 **Context Used:**\n{retrieved_context[:300]}...")  # Show first 300 chars
    print(f"\n❓ **Question:** {query}")
    print(f"\n✅ **Generated Response:** {response}")

    return response

# 🔹 Test with Example Query
query = "In which jurisdictions is the digital asset/cryptocurrency operating?"
response = generate_rag_response(query, documents)
print("\n💬 **Final Answer:**\n", response)
