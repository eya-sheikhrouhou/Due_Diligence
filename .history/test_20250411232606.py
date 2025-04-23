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
from datetime import datetime
from sklearn.feature_extraction.text import TfidfVectorizer
import numpy as np
import pandas as pd
from pptx import Presentation
from pptx.util import Inches

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

# 🔊 Synthèse vocale
def speak_text(text):
    tts = gTTS(text=text)
    temp_file = BytesIO()
    tts.write_to_fp(temp_file)
    temp_file.seek(0)
    audio = AudioSegment.from_file(temp_file, format="mp3")
    audio.export("temp_output.mp3", format="mp3")
    st.audio("temp_output.mp3", format="audio/mp3")

def generate_pptx(session_name, document_text):
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.shapes import MSO_AUTO_SHAPE_TYPE
    from io import BytesIO
    import os

    prs = Presentation()
    blank_slide = prs.slide_layouts[6]

    def add_background(slide, color=RGBColor(20, 25, 40)):
        fill = slide.background.fill
        fill.solid()
        fill.fore_color.rgb = color

    def add_title_slide(title, subtitle, image_path=None):
        slide = prs.slides.add_slide(blank_slide)
        add_background(slide)

        title_box = slide.shapes.add_textbox(Inches(1), Inches(1.2), Inches(8), Inches(1))
        tf = title_box.text_frame
        tf.text = title
        tf.paragraphs[0].font.size = Pt(44)
        tf.paragraphs[0].font.bold = True
        tf.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)

        subtitle_box = slide.shapes.add_textbox(Inches(1), Inches(2.5), Inches(8), Inches(1))
        tf2 = subtitle_box.text_frame
        tf2.text = subtitle
        tf2.paragraphs[0].font.size = Pt(22)
        tf2.paragraphs[0].font.color.rgb = RGBColor(180, 180, 180)

        if image_path and os.path.exists(image_path):
            slide.shapes.add_picture(image_path, Inches(5.5), Inches(0.2), height=Inches(1.0))

    def add_bullet_slide(title, bullets, image=None):
        slide = prs.slides.add_slide(blank_slide)
        add_background(slide, RGBColor(30, 30, 50))

        title_box = slide.shapes.add_textbox(Inches(0.7), Inches(0.5), Inches(8), Inches(1))
        tf_title = title_box.text_frame
        tf_title.text = title
        tf_title.paragraphs[0].font.size = Pt(32)
        tf_title.paragraphs[0].font.bold = True
        tf_title.paragraphs[0].font.color.rgb = RGBColor(255, 215, 0)

        content_box = slide.shapes.add_textbox(Inches(0.9), Inches(1.5), Inches(7), Inches(5))
        tf = content_box.text_frame
        tf.word_wrap = True

        for bullet in bullets:
            p = tf.add_paragraph()
            p.text = bullet.strip()
            p.level = 0
            p.font.size = Pt(20)
            p.font.color.rgb = RGBColor(230, 230, 230)

        if image and os.path.exists(image):
            slide.shapes.add_picture(image, Inches(6.5), Inches(1.4), height=Inches(3.5))

    # --- Découpe du document en sections simples
    chunks = [p.strip() for p in document_text.split("\n") if len(p.strip()) > 40]
    key_points = chunks[:5]
    risks = [c for c in chunks if "risk" in c.lower()][:4]
    reg = [c for c in chunks if "regulation" in c.lower() or "compliance" in c.lower()][:4]
    recs = [c for c in chunks if "recommend" in c.lower() or "suggest" in c.lower()][:4]

    # 🔧 Slides
    add_title_slide("Due Diligence Insights Report", f"Session: {session_name}", image_path="due_diligence_banner.jpg")
    add_bullet_slide("Executive Summary", key_points, image="summary_icon.png")
    add_bullet_slide("Key Findings", key_points, image="insight_icon.png")
    add_bullet_slide("Regulatory Considerations", reg or ["No regulatory content detected."], image="law_icon.png")
    add_bullet_slide("Risks & Mitigation", risks or ["No risk-related content found."], image="risk_icon.png")
    add_bullet_slide("Recommendations", recs or ["No recommendations extracted."], image="recommend_icon.png")
    add_bullet_slide("Conclusion", [
        "This presentation summarizes key insights from the document.",
        "The analysis highlights crucial risks, regulatory concerns and strategies.",
        "Use this as a decision-support tool for compliance or investment teams."
    ], image="check_icon.png")

    pptx_io = BytesIO()
    prs.save(pptx_io)
    pptx_io.seek(0)
    return pptx_io

# 💾 Sauvegarde MongoDB
def save_conversation(session_name, history):
    collection.update_one(
        {"session": session_name},
        {"$set": {"messages": history, "timestamp": datetime.utcnow()}},
        upsert=True
    )

# 🎨 Streamlit config
st.set_page_config("💬 Due Diligence AI", layout="wide")
st.markdown("<h1 style='text-align: center;'>💼 Due Diligence ChatGPT Assistant</h1>", unsafe_allow_html=True)

# 🧾 Session state
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

# 💬 Liste des sessions
st.sidebar.title("💬 Conversations")

# 🔄 Chargement sessions depuis MongoDB
chat_sessions = list(collection.find({}, {"session": 1, "timestamp": 1}).sort("timestamp", -1).limit(10))
session_names = [s["session"] for s in chat_sessions]

# 🆕 Nouveau chat
if st.sidebar.button("➕ New Chat"):
    st.session_state.history = []
    st.session_state.chat_context = dict(cleaned_texts)
    st.session_state.session_name = f"Session-{datetime.utcnow().strftime('%Y%m%d%H%M')}"
    st.rerun()

# 📂 Sélection session existante
selected_session = st.sidebar.selectbox("📚 Load a past chat", session_names)
if selected_session and selected_session != st.session_state.session_name:
    doc = collection.find_one({"session": selected_session})
    if doc:
        st.session_state.session_name = selected_session
        st.session_state.history = doc["messages"]
        st.rerun()

# 💬 Input
question = st.chat_input("Ask a due diligence question...")

# 💬 Affichage de la conversation
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 💡 Traitement du message
if question:
    with st.chat_message("user"):
        st.markdown(question)
    st.session_state.history.append({"role": "user", "content": question})

    with st.spinner("⏳ Thinking..."):
        context = find_relevant_context(question, st.session_state.chat_context)
        answer = generate_answer_with_ollama(question, context)

    with st.chat_message("assistant"):
        st.markdown(answer)
        st.button("🔊 Speak", key=f"speak_{len(st.session_state.history)}", on_click=speak_text, args=(answer,))
    
    st.session_state.history.append({"role": "assistant", "content": answer})
    save_conversation(st.session_state.session_name, st.session_state.history)

# 📤 Export
st.sidebar.title("📤 Export")

# Export CSV
if st.sidebar.button("📁 Export Conversation (.csv)"):
    df = pd.DataFrame(st.session_state.history)
    df.to_csv("conversation.csv", index=False)
    st.sidebar.download_button("⬇️ Download CSV", data=open("conversation.csv", "rb"), file_name="conversation.csv")

# Export PPTX
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
