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
    engine = pyttsx3.init()
    engine.setProperty('rate', 165)
    
    # Créer un fichier temporaire pour stocker l'audio
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_path = temp_file.name
    temp_file.close()

    engine.save_to_file(text, temp_path)
    engine.runAndWait()

    # 🔁 Attendre un peu que le fichier soit écrit (important pour certains systèmes)
    time.sleep(1)

    if os.path.exists(temp_path) and os.path.getsize(temp_path) > 1000:
        st.audio(temp_path, format='audio/mp3')
    else:
        st.error("⚠️ Audio file was not generated correctly.")

# 📤 PowerPoint Générateur
def generate_pptx(session_name, summary_text, key_points=None, logo_path=None):
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)

    COLORS = {
        "dark_blue": RGBColor(0, 32, 96),
        "medium_blue": RGBColor(0, 84, 159),
        "light_blue": RGBColor(142, 186, 229),
        "accent_gold": RGBColor(212, 175, 55),
        "dark_gray": RGBColor(51, 51, 51),
        "light_gray": RGBColor(238, 238, 238),
        "white": RGBColor(255, 255, 255)
    }

    def add_title_slide():
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = COLORS["dark_blue"]

        if logo_path and os.path.exists(logo_path):
            slide.shapes.add_picture(logo_path, Inches(10.5), Inches(0.3), height=Inches(0.8))

        title = slide.shapes.add_textbox(Inches(1), Inches(2), Inches(11), Inches(1.5))
        tf = title.text_frame
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = "DUE DILIGENCE SUMMARY"
        run.font.size = Pt(44)
        run.font.bold = True
        run.font.color.rgb = COLORS["white"]
        p.alignment = PP_ALIGN.LEFT

        subtitle = slide.shapes.add_textbox(Inches(1), Inches(3.2), Inches(11), Inches(1))
        tf2 = subtitle.text_frame
        p2 = tf2.paragraphs[0]
        run2 = p2.add_run()
        run2.text = "Comprehensive Analysis Report"
        run2.font.size = Pt(24)
        run2.font.color.rgb = COLORS["light_blue"]

        info = slide.shapes.add_textbox(Inches(1), Inches(4.2), Inches(11), Inches(1))
        tf3 = info.text_frame
        p3 = tf3.paragraphs[0]
        run3 = p3.add_run()
        run3.text = f"Session: {session_name}\nDate: {datetime.today().strftime('%B %d, %Y')}"
        run3.font.size = Pt(18)
        run3.font.color.rgb = COLORS["white"]

        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, Inches(6.5), prs.slide_width, Inches(0.2))
        line.fill.solid()
        line.fill.fore_color.rgb = COLORS["accent_gold"]

    def add_summary_slide():
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = COLORS["light_gray"]

        header = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12), Inches(1))
        tf = header.text_frame
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = "EXECUTIVE SUMMARY"
        run.font.size = Pt(32)
        run.font.bold = True
        run.font.color.rgb = COLORS["dark_blue"]

        line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(1.2), Inches(12), Inches(0.05))
        line.fill.solid()
        line.fill.fore_color.rgb = COLORS["medium_blue"]

        content = slide.shapes.add_textbox(Inches(0.5), Inches(1.5), Inches(12), Inches(5))
        tf2 = content.text_frame
        tf2.word_wrap = True
        for i, para in enumerate(summary_text.strip().split("\n\n")):
            p = tf2.add_paragraph()
            p.text = para
            p.font.size = Pt(18)
            p.font.color.rgb = COLORS["dark_gray"]
            if i == 0:
                p.font.bold = True

    def add_recommendations_slide():
        slide = prs.slides.add_slide(prs.slide_layouts[6])
        bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
        bg.fill.solid()
        bg.fill.fore_color.rgb = COLORS["white"]

        header = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12), Inches(1))
        tf = header.text_frame
        p = tf.paragraphs[0]
        run = p.add_run()
        run.text = "\ud83d\udd0d KEY RECOMMENDATIONS"
        run.font.size = Pt(32)
        run.font.bold = True
        run.font.color.rgb = COLORS["dark_blue"]

        bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(1.2), Inches(1.5), Inches(0.1))
        bar.fill.solid()
        bar.fill.fore_color.rgb = COLORS["accent_gold"]

        bullet_box = slide.shapes.add_textbox(Inches(1), Inches(1.7), Inches(11), Inches(4.6))
        tf2 = bullet_box.text_frame
        tf2.word_wrap = True
        bullets = key_points or [
            "Ensure compliance with KYC/AML & financial regulations",
            "Reinforce risk policies for digital asset transactions",
            "Audit document flows and ownership structures",
            "Improve market volatility protection mechanisms",
            "Harden cybersecurity systems and access controls"
        ]
        for bullet in bullets:
            p = tf2.add_paragraph()
            p.text = bullet
            p.font.size = Pt(18)
            p.font.color.rgb = COLORS["dark_gray"]

    # Build slides
    add_title_slide()
    add_summary_slide()
    add_recommendations_slide()

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
    st.sidebar.success("✅ Document loaded.")

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
        pptx_file = generate_pptx(st.session_state.session_name, raw_doc_text)
        st.sidebar.download_button(
            label="⬇️ Download PPTX",
            data=pptx_file,
            file_name=f"{st.session_state.session_name}_report.pptx",
            mime="application/vnd.openxmlformats-officedocument.presentationml.presentation"
        )
    else:
        st.sidebar.warning("❗ Please upload a document and ask at least one question before exporting.")
