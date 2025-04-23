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

# Environnement & DB
os.environ["OLLAMA_NUM_GPU_LAYERS"] = "100"
client = MongoClient("mongodb://localhost:27017/")
db = client["due_diligence"]
collection = db["qa_sessions"]

# 📜 Textes nettoyés
cleaned_texts_dir = "cleaned_texts"
cleaned_texts = {txt_file: open(txt_file, "r", encoding="utf-8").read() for txt_file in glob.glob(f"{cleaned_texts_dir}/*.txt")}

MODEL_NAME = "mistral:latest"

# 🔍 Contexte via TF-IDF
def find_relevant_context(question, texts, max_words=300):
    if not texts: return ""
    vectorizer = TfidfVectorizer(stop_words="english")
    corpus = list(texts.values()) + [question]
    tfidf_matrix = vectorizer.fit_transform(corpus)
    similarity_scores = (tfidf_matrix[-1] @ tfidf_matrix[:-1].T).toarray()[0]
    best_match_idx = np.argmax(similarity_scores)
    return list(texts.values())[best_match_idx][:max_words]

# 🤖 Réponse via Ollama
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

# 📥 Texte depuis PDF ou TXT
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

# 🎤 Entrée vocale
def transcribe_audio():
    recognizer = sr.Recognizer()
    with sr.Microphone() as source:
        st.info("🎤 Speak now...")
        audio = recognizer.listen(source)
    try:
        return recognizer.recognize_google(audio)
    except sr.UnknownValueError:
        return "Sorry, I couldn't understand the audio."

# 🔊 Synthèse vocale
def speak_text(text):
    tts = gTTS(text=text)
    temp_file = BytesIO()
    tts.write_to_fp(temp_file)
    temp_file.seek(0)
    audio = AudioSegment.from_file(temp_file, format="mp3")
    audio.export("temp_output.mp3", format="mp3")
    st.audio("temp_output.mp3", format="audio/mp3")

# 💾 Enregistrement MongoDB
def save_conversation(session_name, history):
    collection.update_one(
        {"session": session_name},
        {"$set": {"messages": history, "timestamp": datetime.utcnow()}},
        upsert=True
    )

# 🎨 UI
st.set_page_config("💬 Due Diligence AI", layout="wide")
st.markdown("<h1 style='text-align: center;'>💼 Due Diligence ChatGPT Assistant</h1>", unsafe_allow_html=True)

# 🧾 Init sessions
if "history" not in st.session_state:
    st.session_state.history = []
if "chat_context" not in st.session_state:
    st.session_state.chat_context = dict(cleaned_texts)
if "session_name" not in st.session_state:
    st.session_state.session_name = f"Session-{datetime.utcnow().strftime('%Y%m%d%H%M')}"

# 📎 Upload PDF/TXT
st.sidebar.title("📎 Document Context")
uploaded_file = st.sidebar.file_uploader("Upload .pdf or .txt", type=["pdf", "txt"])
if uploaded_file:
    doc_text = extract_text_from_file(uploaded_file)
    st.session_state.chat_context = {uploaded_file.name: doc_text}
    st.sidebar.success("✅ Document loaded.")

# 💬 Liste des conversations (historique MongoDB)
st.sidebar.title("💬 Conversations")
chat_sessions = list(collection.find({}, {"session": 1, "timestamp": 1}).sort("timestamp", -1).limit(10))
session_names = [s["session"] for s in chat_sessions]
selected_session = st.sidebar.selectbox("📚 Load a past chat", session_names)

if selected_session and selected_session != st.session_state.session_name:
    doc = collection.find_one({"session": selected_session})
    if doc:
        st.session_state.session_name = selected_session
        st.session_state.history = doc["messages"]
        st.rerun()
# 🎤 Entrée vocale
if st.sidebar.button("🎙️ Use Voice"):
    question = transcribe_audio()
else:
    question = st.chat_input("Ask a due diligence question...")

# 💬 Affichage style ChatGPT
for msg in st.session_state.history:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ✅ Gestion du prompt soumis
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

# 📤 Export CSV
st.sidebar.title("📤 Export")
if st.sidebar.button("📁 Export Conversation"):
    df = pd.DataFrame(st.session_state.history)
    df.to_csv("conversation.csv", index=False)
    st.sidebar.download_button("⬇️ Download CSV", data=open("conversation.csv", "rb"), file_name="conversation.csv")
