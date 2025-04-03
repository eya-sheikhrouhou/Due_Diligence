import os
import PyPDF2
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

# Trouver tous les fichiers PDF dans le dossier
pdf_files = [f for f in os.listdir() if f.endswith(".pdf")]
print(f"📄 Fichiers PDF trouvés : {len(pdf_files)}")

# Lire et extraire le texte de tous les PDFs
all_text = ""
for pdf_file in pdf_files:
    print(f"Lecture de : {pdf_file}")
    with open(pdf_file, "rb") as file:
        pdf_reader = PyPDF2.PdfReader(file)
        for page in pdf_reader.pages:
            extracted_text = page.extract_text()
            if extracted_text:
                all_text += extracted_text
            else:
                print(f"⚠️ Aucune texte extraite de cette page dans {pdf_file}")

# Vérifier si du texte a été extrait
if not all_text:
    print("❌ Erreur : Aucun texte extrait des PDFs. Vérifie les fichiers.")
    exit()

print(f"✅ Texte total extrait : {len(all_text)} caractères")

# Découper en morceaux de 500 caractères
chunk_size = 500
chunks = [all_text[i:i + chunk_size] for i in range(0, len(all_text), chunk_size)]
print(f"✂️ Nombre de morceaux créés : {len(chunks)}")

# Vérifier si des morceaux existent
if not chunks:
    print("❌ Erreur : Aucun morceau créé. Le texte est trop court ou vide.")
    exit()

# Transformer en codes numériques et créer une carte
embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
embeddings = embed_model.encode(chunks)
print(f"🔢 Embeddings générés : {embeddings.shape}")

# Vérifier la forme des embeddings
if embeddings.size == 0 or len(embeddings.shape) < 2:
    print("❌ Erreur : Les embeddings sont vides ou mal formés.")
    exit()

dimension = embeddings.shape[1]
index = faiss.IndexFlatL2(dimension)
index.add(embeddings)

# Sauvegarder
faiss.write_index(index, "faiss_index.bin")
np.save("text_chunks.npy", np.array(chunks, dtype=object))

print("✅ Tous les PDFs sont traités et sauvegardés !")