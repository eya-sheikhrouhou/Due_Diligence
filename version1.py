import fitz  # PyMuPDF
import os
from pymongo import MongoClient
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import streamlit as st
from langchain_community.llms import Ollama
import re

# Connexion MongoDB
client = MongoClient('mongodb://localhost:27017/')
db = client['crypto_due_diligence']
questions_collection = db['questions']

def fetch_questions_from_db():
    questions = questions_collection.find()
    return [question['text'] for question in questions]

def calculate_similarity(question_text, answer_text):
    vectorizer = TfidfVectorizer().fit_transform([question_text, answer_text])
    similarity_matrix = cosine_similarity(vectorizer[0:1], vectorizer[1:2])
    return similarity_matrix[0][0]

def extract_text_from_pdf(pdf_bytes):
    with open("temp_uploaded.pdf", "wb") as f:
        f.write(pdf_bytes)
    doc = fitz.open("temp_uploaded.pdf")
    text = ""
    for page in doc:
        text += page.get_text("text")
    doc.close()
    os.remove("temp_uploaded.pdf")
    return text

def split_text_into_sections_advanced(pdf_text):
    # Dictionnaire des mots-clés par thème
    keywords = {
        "Legal": ["legal", "juridique", "securities", "regulatory", "laws"],
        "Compliance": ["compliance", "illicit", "criminal", "audit", "regulations", "regulatory risk"],
        "Ecology": ["ecology", "environmental", "carbon", "emissions", "sustainability"],
        "Social": ["social", "community", "user base", "engagement", "inclusion", "ethics"],
        "Governance": ["governance", "dao", "voting", "decision making", "transparency", "structure"],
    }

    # Init des sections
    sections = {k: "" for k in keywords}
    lines = pdf_text.split("\n")
    current_section = None

    for line in lines:
        line_clean = line.strip().lower()
        if len(line_clean) < 100:
            for section, word_list in keywords.items():
                if any(kw in line_clean for kw in word_list):
                    current_section = section
                    break
        if current_section:
            sections[current_section] += line + "\n"

    return sections

def analyze_sections_with_questions(sections, user_questions):
    section_scores = {}
    for section, content in sections.items():
        scores = []
        for user_question in user_questions:
            score = calculate_similarity(user_question, content)
            scores.append(score)
        section_scores[section] = sum(scores) / len(scores) if scores else 0.0
    return section_scores

def chatbot(query, sections):
    llm = Ollama(model="mistral")
    context = "\n".join([f"{section}: {content[:200]}" for section, content in sections.items()])
    prompt = f"Question: {query}\n\nContext: {context}\nAnswer: "
    response = llm(prompt)
    return response

# --------------------------- STREAMLIT INTERFACE ---------------------------
def main():
    st.set_page_config(page_title="Crypto Due Diligence Assistant", layout="wide")
    st.title("📄 Crypto Due Diligence Assistant")

    uploaded_file = st.file_uploader("📎 Importer un fichier PDF", type="pdf")

    if uploaded_file is not None:
        with st.spinner("📖 Lecture du fichier..."):
            pdf_text = extract_text_from_pdf(uploaded_file.read())
            st.success("Fichier lu avec succès !")

        st.subheader("📝 Aperçu du contenu")
        st.write(pdf_text[:500] + "...")

        sections = split_text_into_sections_advanced(pdf_text)

        st.subheader("🧩 Sections détectées")
        for section, content in sections.items():
            st.write(f"**{section}:** {content[:300]}...")

        user_questions = fetch_questions_from_db()
        section_scores = analyze_sections_with_questions(sections, user_questions)

        st.subheader("📊 Score de chaque section (basé sur les similarités)")
        for section, score in section_scores.items():
            st.write(f"**{section}**: {score:.2f}")

        st.subheader("🤖 Posez une question sur le contenu analysé")
        user_input = st.text_input("Votre question ici:")
        if user_input:
            response = chatbot(user_input, sections)
            st.write(f"Réponse du chatbot: {response}")

        if st.button("📥 Générer un rapport"):
            report = "Rapport de Due Diligence:\n\n"
            for section, score in section_scores.items():
                report += f"{section}: {score:.2f}\n"
            st.download_button(label="📎 Télécharger le rapport", data=report, file_name="rapport_due_diligence.txt")

if __name__ == "__main__":
    main()
