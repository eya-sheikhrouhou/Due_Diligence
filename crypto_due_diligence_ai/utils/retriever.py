from langchain.vectorstores import FAISS
from langchain.embeddings import OllamaEmbeddings
from langchain.text_splitter import CharacterTextSplitter

def create_vectorstore(text):
    splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=100)
    chunks = splitter.split_text(text)
    embeddings = OllamaEmbeddings(model="mistral")
    vectordb = FAISS.from_texts(chunks, embedding=embeddings)
    return vectordb

def retrieve_docs(vectordb, query):
    return vectordb.similarity_search(query, k=4)
