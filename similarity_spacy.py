import streamlit as st
import fitz  # PyMuPDF
import spacy
import os

# Charger le modèle spaCy
nlp = spacy.load("en_core_web_md")

st.title("🔍 Crypto Due Diligence - Similarité avec spaCy")

# Charger et parser le fichier PDF
uploaded_file = st.file_uploader("📄 Uploadez un document PDF", type="pdf")

def extract_text_from_pdf(file):
    doc = fitz.open(stream=file.read(), filetype="pdf")
    text = ""
    for page in doc:
        text += page.get_text()
    return text

# Exemple de questions
questions = [
    "Does the project comply with US regulations?",
    "Is there any ecological impact?",
    "Are the founders identified?",
    "Is there a clear governance structure?",
    "Does the token have utility?"
]

def compute_similarity(text, questions, threshold=0.7):
    results = []
    doc_text = nlp(text)
    for q in questions:
        doc_q = nlp(q)
        score = doc_q.similarity(doc_text)
        results.append((q, round(score, 2)))
    return results

if uploaded_file:
    st.success("✅ Fichier chargé avec succès.")
    extracted_text = extract_text_from_pdf(uploaded_file)
    
    st.subheader("📌 Questions et scores de similarité")
    similarity_results = compute_similarity(extracted_text, questions)
    
    for q, score in similarity_results:
        st.write(f"**{q}** → Similarité : `{score}` {'🟢' if score >= 0.7 else '🔴'}")
