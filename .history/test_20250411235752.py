# 📦 Importations
import os
import streamlit as st
import ollama
import glob
import pdfplumber
import PyPDF2
import speech_recognition as sr
from gtts import gTTS
from pydub import AudioSegment
from io import BytesIO
from pymongo import MongoClient
from datetime import datetime, timezone
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import pandas as pd
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor

# 🌍 Environnement
os.environ["OLLAMA_NUM_GPU_LAYERS"] = "100"

# 🔗 MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["due_diligence"]
collection = db["qa_sessions"]

# 🤖 Modèle
MODEL_NAME = "mistral:latest"

# 📁 Charger textes nettoyés si dispo
cleaned_texts_dir = "cleaned_texts"
cleaned_texts = {f: open(f, "r", encoding="utf-8").read() for f in glob.glob(f"{cleaned_texts_dir}/*.txt")}

# 🔎 TF-IDF Search
def find_relevant_context(question, texts, max_words=300):
    if not texts: return ""
    vectorizer = TfidfVectorizer(stop_words="english")
    corpus = list(texts.values()) + [question]
    tfidf_matrix = vectorizer.fit_transform(corpus)
    scores = (tfidf_matrix[-1] @ tfidf_matrix[:-1].T).toarray()[0]
    return list(texts.values())[np.argmax(scores)][:max_words]

# 🧠 LLM Response
def generate_answer_with_ollama(question, context):
    if not context.strip():
        context = "No specific context available."
    prompt = f"""You are a due diligence expert. Use the CONTEXT below if possible.

CONTEXT:
{context}

QUESTION:
{question}

INSTRUCTIONS:
- Be complete (min 4 sentences).
- If context is lacking, answer with industry knowledge.

ANSWER:"""
    response = ollama.chat(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}], options={"num_predict": 250})
    return response['message']['content'].strip()

# 📄 Fichier texte
def extract_text_from_file(uploaded_file):
    if uploaded_file.name.endswith(".txt"):
        return uploaded_file.read().decode("utf-8")
    elif uploaded_file.name.endswith(".pdf"):
        with pdfplumber.open(uploaded_file) as pdf:
            return "\n".join(p.extract_text() or "" for p in pdf.pages)
    return ""

# 🔊 Voix
def speak_text(text):
    tts = gTTS(text)
    temp = BytesIO()
    tts.write_to_fp(temp)
    temp.seek(0)
    audio = AudioSegment.from_file(temp, format="mp3")
    audio.export("temp_output.mp3", format="mp3")
    st.audio("temp_output.mp3", format="audio/mp3")

# 📊 PPTX Génération
def generate_pptx(session_name, document_text):
    prs = Presentation()
    layout = prs.slide_layouts[6]

    def add_slide(title, bullets, color, image=None):
        slide = prs.slides.add_slide(layout)
        slide.background.fill.solid()
        slide.background.fill.fore_color.rgb = color

        title_box = slide.shapes.add_textbox(Inches(0.7), Inches(0.5), Inches(8), Inches(1))
        tf = title_box.text_frame
        tf.text = title
        tf.paragraphs[0].font.size = Pt(32)
        tf.paragraphs[0].font.bold = True
        tf.paragraphs[0].font.color.rgb = RGBColor(255, 215, 0)

        content_box = slide.shapes.add_textbox(Inches(1), Inches(1.5), Inches(7), Inches(5))
        for b in bullets:
            p = content_box.text_frame.add_paragraph()
            p.text = b.strip()
            p.font.size = Pt(20)
            p.font.color.rgb = RGBColor(230, 230, 230)

        if image and os.path.exists(image):
            slide.shapes.add_picture(image, Inches(6.5), Inches(1.4), height=Inches(3.5))

    # ➕ Sections
    chunks = [p.strip() for p in document_text.split("\n") if len(p.strip()) > 40]
    key = chunks[:5]
    risks = [c for c in chunks if "risk" in c.lower()][:4]
    regs = [c for c in chunks if "regulation" in c.lower() or "compliance" in c.lower()][:4]
    recs = [c for c in chunks if "recommend" in c.lower() or "suggest" in c.lower()][:4]

    # 📊 Slides
    add_slide("Executive Summary", key, RGBColor(30, 30, 50), "summary_icon.png")
    add_slide("Key Findings", key, RGBColor(30, 30, 50), "insight_icon.png")
    add_slide("Risks", risks or ["No risk-related content found."], RGBColor(30, 30, 50), "risk_icon.png")
    add_slide("Regulatory", regs or ["No regulatory information found."], RGBColor(30, 30, 50), "law_icon.png")
    add_slide("Recommendations", recs or ["No recommendations found."], RGBColor(30, 30, 50), "recommend_icon.png")

    final = BytesIO()
    prs.save(final)
    final.seek(0)
    return final

# 🗂️ Sauvegarde
def save_conversation(session_name, history):
    collection.update_one(
        {"session": session_name},
        {"$set": {"messages": history, "timestamp": datetime.now(timezone.utc)}},
        upsert=True
    )

# 🌐 Interface Streamlit
st.set_page_config(page_title="Due Diligence Chat", layout="wide")
st.markdown("<h1 style='text-align: center;'>💼 Due Diligence Assistant</h1>", unsafe_allow_html=True)

# 💾 Session
if "history" not in st.session_state: st.session_state.history = []
if "chat_context" not in st.session_state: st.session_state.chat_context = dict(cleaned_texts)
if "session_name" not in st.session_state: st.session_state.session_name = f"Session-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"

# 📁 Upload fichier
st.sidebar.title("📎 Document Context")
uploaded_file = st.sidebar.file_uploader("Upload .pdf or .txt", type=["pdf", "txt"])
if uploaded_file:
    st.session_state.chat_context = {uploaded_file.name: extract_text_from_file(uploaded_file)}
    st.sidebar.success("✅ Document uploaded!")

# 🆕 Nouveau chat
if st.sidebar.button("➕ New Chat"):
    prev_texts = dict(cleaned_texts)
    st.session_state.clear()
    st.session_state.chat_context = prev_texts
    st.session_state.history = []
    st.session_state.session_name = f"Session-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M')}"
    st.rerun()

# 📚 Historique
chat_sessions = list(collection.find({}, {"session": 1}).sort("timestamp", -1).limit(10))
options = [s["session"] for s in chat_sessions]
sel = st.sidebar.selectbox("📚 Load a past chat", options)
if sel and sel != st.session_state.session_name:
    doc = collection.find_one({"session": sel})
    if doc:
        st.session_state.session_name = sel
        st.session_state.history = doc["messages"]
        st.rerun()

# 💬 Interaction
question = st.chat_input("Ask a due diligence question...")
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

if question:
    st.session_state.history.append({"role": "user", "content": question})
    with st.spinner("⏳ Thinking..."):
        ctx = find_relevant_context(question, st.session_state.chat_context)
        ans = generate_answer_with_ollama(question, ctx)
    st.session_state.history.append({"role": "assistant", "content": ans})
    save_conversation(st.session_state.session_name, st.session_state.history)

    with st.chat_message("assistant"):
        st.markdown(ans)
        st.button("🔊 Speak", on_click=speak_text, args=(ans,), key=f"speak_{len(st.session_state.history)}")

# 📤 Export
st.sidebar.title("📤 Export")
if st.sidebar.button("📁 Export CSV"):
    df = pd.DataFrame(st.session_state.history)
    df.to_csv("conversation.csv", index=False)
    st.sidebar.download_button("⬇️ Download CSV", open("conversation.csv", "rb"), "conversation.csv")

if st.sidebar.button("📊 Export PPTX"):
    if st.session_state.chat_context and st.session_state.history:
        raw = list(st.session_state.chat_context.values())[0]
        pptx = generate_pptx(st.session_state.session_name, raw)
        st.sidebar.download_button("⬇️ Download PPTX", pptx, f"{st.session_state.session_name}.pptx", "application/vnd.openxmlformats-officedocument.presentationml.presentation")
    else:
        st.sidebar.warning("❗ Upload a document and ask a question first.")
