import streamlit as st
from utils.loader import load_pdf
from utils.retriever import create_vectorstore, retrieve_docs
from utils.qa import ask_question, improve_answer
from utils.ppt_generator import generate_ppt
from utils.voice import speak_answer

st.set_page_config(page_title="Crypto Due Diligence Agent", layout="wide")
st.title("🧠 Crypto Due Diligence AI Agent")

if "history" not in st.session_state:
    st.session_state.history = []

uploaded_file = st.file_uploader("📄 Upload a crypto project PDF", type="pdf")

if uploaded_file:
    st.success("Document uploaded successfully.")
    text = load_pdf(uploaded_file)
    vectordb = create_vectorstore(text)

    st.session_state["vectordb"] = vectordb
    st.session_state["doc_text"] = text

if "vectordb" in st.session_state:
    question = st.text_input("🔎 Ask a due diligence question about the project:")

    if question:
        with st.spinner("Thinking..."):
            docs = retrieve_docs(st.session_state["vectordb"], question)
            answer, flagged = ask_question(question, docs)

            st.session_state.history.append({"question": question, "answer": answer, "flagged": flagged})

            st.markdown("### 🤖 Answer")
            st.write(answer)

            if st.button("🔊 Read Answer Aloud"):
                speak_answer(answer)

            if flagged:
                st.error("⚠️ Potential Red Flag detected in the response!")

            st.markdown("---")

            if st.button("📊 Generate PowerPoint Report"):
                pptx_file = generate_ppt(question, answer, flagged)
                st.success("Report generated.")
                st.download_button("⬇️ Download Report", pptx_file, file_name="due_diligence_report.pptx")

# Historique des Q&A
if st.session_state.history:
    st.markdown("## 🕘 Question History")
    for i, entry in enumerate(reversed(st.session_state.history), 1):
        st.markdown(f"**Q{i}:** {entry['question']}")
        st.markdown(f"**A{i}:** {entry['answer']}")
        if entry['flagged']:
            st.markdown("⚠️ _Red Flag Detected_")
        if st.button(f"✨ Improve Answer {i}"):
            with st.spinner("Refining answer..."):
                improved = improve_answer(entry['question'], entry['answer'])
                entry['answer'] = improved
                st.success("Answer improved!")
                st.markdown(f"**🔁 New A{i}:** {improved}")
        if st.button(f"🔊 Read A{i}"):
            speak_answer(entry['answer'])
        st.markdown("---")