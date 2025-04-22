import os
import streamlit as st
import ollama
import glob
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN

import pdfplumber
import PyPDF2
import speech_recognition as sr
from io import BytesIO
from pymongo import MongoClient
from datetime import datetime, timezone
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import pandas as pd
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
import pyttsx3
import tempfile
import pyttsx3
import tempfile
import time
import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE

# ⛓️ Environnement & DB
os.environ["OLLAMA_NUM_GPU_LAYERS"] = "100"
client = MongoClient("mongodb://localhost:27017/")
db = client["due_diligence"]
collection = db["qa_sessions"]

MODEL_NAME = "mistral:latest"

# 📜 Préchargement de textes si dispos
cleaned_texts_dir = "cleaned_texts"
cleaned_texts = {txt_file: open(txt_file, "r", encoding="utf-8").read() for txt_file in glob.glob(f"{cleaned_texts_dir}/*.txt")}

# 🔍 Recherche de contexte
def find_relevant_context(question, texts, max_words=300):
    if not texts: return ""
    vectorizer = TfidfVectorizer(stop_words="english")
    corpus = list(texts.values()) + [question]
    tfidf_matrix = vectorizer.fit_transform(corpus)
    similarity_scores = (tfidf_matrix[-1] @ tfidf_matrix[:-1].T).toarray()[0]
    best_match_idx = np.argmax(similarity_scores)
    return list(texts.values())[best_match_idx][:max_words]

# 🤖 Appel Ollama
def generate_answer_with_ollama(question, context):
    if not context.strip():
        context = "No specific context available. Please answer based on your digital finance expertise."
    prompt = f"""
    You are a due diligence expert. Answer the question below using only this context if possible:

    CONTEXT:
    {context}

    QUESTION:
    {question}

    INSTRUCTIONS:
    - Be complete, minimum 4 sentences.
    - If context is insufficient, answer with industry knowledge and suggest additional details needed.

    ANSWER:
    """
    response = ollama.chat(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}], options={"num_predict": 250})
    return response['message']['content'].strip()

# 📄 Lecture fichier
def extract_text_from_file(uploaded_file):
    ext = uploaded_file.name.lower()
    text = ""
    if ext.endswith(".txt"):
        text = uploaded_file.read().decode("utf-8")
    elif ext.endswith(".pdf"):
        with pdfplumber.open(uploaded_file) as pdf:
            for page in pdf.pages:
                content = page.extract_text()
                if content:
                    text += content + "\n"
    return text

def speak_text(text):
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 165)

        # 🔊 Liste les voix installées (optionnel pour debug)
        voices = engine.getProperty('voices')
        print("Voices disponibles:")
        for v in voices:
            print(f"- {v.id} ({v.name})")

        # Optionnel : choisir une voix spécifique
        # engine.setProperty('voice', voices[0].id)

        # Crée un fichier temporaire pour l'audio
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp_path = temp_file.name
        temp_file.close()

        engine.save_to_file(text, temp_path)
        engine.runAndWait()
        time.sleep(1)

        if os.path.exists(temp_path) and os.path.getsize(temp_path) > 1000:
            st.audio(temp_path, format='audio/wav')
        else:
            st.error("⚠️ Fichier audio non généré ou vide.")
            print("⚠️ Audio file path:", temp_path)

    except Exception as e:
        st.error(f"Erreur synthèse vocale : {e}")
        print(f"Exception dans speak_text: {e}")

def detect_red_flags(text):
    red_flags = ["ponzi", "scam", "non audited", "data breach", "offshore", "non compliant", "suspicious"]
    detected = [flag for flag in red_flags if flag.lower() in text.lower()]
    return detected        

# 📤 PowerPoint Générateur

def generate_pptx(session_name, summary_text, key_points=None, template_path=None):
    # Charger la présentation depuis le modèle
    if not template_path or not os.path.exists(template_path):
        raise FileNotFoundError("Le modèle PowerPoint est introuvable.")

    prs = Presentation(template_path)

    # Remplacer les espaces réservés du modèle
    def replace_placeholders(slide):
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            for paragraph in shape.text_frame.paragraphs:
                for run in paragraph.runs:
                    run.text = run.text.replace("[Target Company Name]", session_name)
                    run.text = run.text.replace("[Client Company Name]", "Confidential Client")
                    run.text = run.text.replace("[Your Name/Firm]", "Due Diligence AI")
                    run.text = run.text.replace("[Date]", datetime.today().strftime('%B %d, %Y'))

    for slide in prs.slides:
        replace_placeholders(slide)

    # Ajouter une slide de résumé dynamique
    def add_summary_slide(text):
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        title_box = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(12), Inches(1))
        title_frame = title_box.text_frame
        title_frame.text = "Executive Summary"
        title_frame.paragraphs[0].runs[0].font.size = Pt(32)
        title_frame.paragraphs[0].runs[0].font.bold = True

        body_box = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(12), Inches(5.5))
        body_frame = body_box.text_frame
        body_frame.word_wrap = True
        for para in text.split("\n"):
            p = body_frame.add_paragraph()
            p.text = para.strip()
            p.font.size = Pt(14)

    add_summary_slide(summary_text[:2000])  # Tronqué si trop long

    # Ajouter une slide de recommandations si nécessaire
    def add_recommendations_slide():
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        box = slide.shapes.add_textbox(Inches(0.5), Inches(0.5), Inches(12), Inches(6))
        tf = box.text_frame
        tf.text = "Key Recommendations"
        tf.paragraphs[0].runs[0].font.size = Pt(32)
        tf.paragraphs[0].runs[0].font.bold = True

        recs = key_points or [
            "Ensure compliance with KYC/AML regulations.",
            "Audit all financial statements and ownership structures.",
            "Enhance cybersecurity measures and data privacy controls.",
            "Evaluate market volatility exposure and stress test mechanisms."
        ]

        for rec in recs:
            p = tf.add_paragraph()
            p.text = f"• {rec}"
            p.level = 0
            p.font.size = Pt(18)

    add_recommendations_slide()

    # Sauvegarder en mémoire
    pptx_io = BytesIO()
    prs.save(pptx_io)
    pptx_io.seek(0)
    return pptx_io

# 💾 Sauvegarde MongoDB
def save_conversation(session_name, history):
    collection.update_one(
        {"session": session_name},
        {"$set": {"messages": history, "timestamp": datetime.now(timezone.utc)}},
        upsert=True
    )

# 🎨 Streamlit config
st.set_page_config("💬 Due Diligence AI", layout="wide")
st.markdown("<h1 style='text-align: center;'>💼 Due Diligence ChatGPT Assistant</h1>", unsafe_allow_html=True)

# 🧾 Session state init
if "history" not in st.session_state:
    st.session_state.history = []
if "chat_context" not in st.session_state:
    st.session_state.chat_context = dict(cleaned_texts)
if "session_name" not in st.session_state:
    st.session_state.session_name = f"Session-{datetime.utcnow().strftime('%Y%m%d%H%M')}"

# 📎 Upload document
st.sidebar.title("📎 Document Context")
uploaded_file = st.sidebar.file_uploader("Upload .pdf or .txt", type=["pdf", "txt"])
if uploaded_file:
    doc_text = extract_text_from_file(uploaded_file)
    st.session_state.chat_context = {uploaded_file.name: doc_text}

    flags = detect_red_flags(doc_text)
    if flags:
        st.sidebar.error(f"⚠️ Red flags detected: {', '.join(flags)}")
    else:
        st.sidebar.success("✅ Document loaded without detected risks.")

# 🆕 New Chat
if st.sidebar.button("➕ New Chat"):
    st.session_state.update({
        "history": [],
        "chat_context": dict(cleaned_texts),
        "session_name": f"Session-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
    })
    st.rerun()

# 💬 Historique sessions
chat_sessions = list(collection.find({}, {"session": 1, "timestamp": 1}).sort("timestamp", -1).limit(10))
session_names = [s["session"] for s in chat_sessions]

selected_session = st.sidebar.selectbox("📚 Load a past chat", session_names)
if selected_session and selected_session != st.session_state.session_name:
    doc = collection.find_one({"session": selected_session})
    if doc:
        st.session_state.session_name = selected_session
        st.session_state.history = doc["messages"]
        st.rerun()

# 💬 Chat
question = st.chat_input("Ask a due diligence question...")
if question:
    with st.chat_message("user"):
        st.markdown(question)
    st.session_state.history.append({"role": "user", "content": question})

    with st.spinner("⏳ Thinking..."):
        context = find_relevant_context(question, st.session_state.chat_context)
        answer = generate_answer_with_ollama(question, context)

    st.session_state.history.append({"role": "assistant", "content": answer})
    save_conversation(st.session_state.session_name, st.session_state.history)

# 💬 Affichage messages + Lecture audio
for i, msg in enumerate(st.session_state.history):
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

        # ✅ Affiche bouton "Speak" uniquement pour les messages de l'assistant
        if msg["role"] == "assistant":
            if st.button(f"🔊 Speak {i}", key=f"speak_{i}"):
                speak_text(msg["content"])


# 📤 Export
st.sidebar.title("📤 Export")

if st.sidebar.button("📁 Export Conversation (.csv)"):
    df = pd.DataFrame(st.session_state.history)
    df.to_csv("conversation.csv", index=False)
    st.sidebar.download_button("⬇️ Download CSV", data=open("conversation.csv", "rb"), file_name="conversation.csv")

if st.sidebar.button("📊 Export PowerPoint (.pptx)"):
    if st.session_state.chat_context and st.session_state.history:
        raw_doc_text = list(st.session_state.chat_context.values())[0]
        pptx_file = generate_pptx(st.session_state.session_name, raw_doc_text,    template_path="/Users/yass/Desktop/Financial-Due-Diligence-Target-Company-Name (1).pptx")
        st.sidebar.download_button(
            label="⬇️ Download PPTX",
            data=pptx_file,
            file_name=f"{st.session_state.session_name}_report.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
    else:
        st.sidebar.warning("❗ Please upload a document and ask at least one question before exporting.")