def show_due_diligence_app():
    from gridfs import GridFS    
    import os
    import streamlit as st
    import ollama
    import glob
    from pptx.enum.shapes import MSO_SHAPE
    from pptx.enum.text import PP_ALIGN
    import re
    import bcrypt
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
    from fpdf import FPDF
    import os
    from pptx import Presentation
    from pptx.util import Inches, Pt
    from pptx.dml.color import RGBColor
    from pptx.enum.text import PP_ALIGN
    from pptx.enum.shapes import MSO_SHAPE
    from datetime import datetime, timezone
    from ExtractionNLP import extract_text_from_pdf, clean_text, summarize_text

  

    # ⛓️ Environnement & DB
    os.environ["OLLAMA_NUM_GPU_LAYERS"] = "100"
    client = MongoClient("mongodb://localhost:27017/")
    db = client["due_diligence"]
    collection = db["qa_sessions"]

    if "history" not in st.session_state:
        st.session_state.history = []

    if "chat_context" not in st.session_state:
        cleaned_texts_dir = "cleaned_texts"
        cleaned_texts = {
            txt_file: open(txt_file, "r", encoding="utf-8").read()
            for txt_file in glob.glob(f"{cleaned_texts_dir}/*.txt")
        }
        st.session_state.chat_context = dict(cleaned_texts)

    if "session_name" not in st.session_state:
        st.session_state.session_name = f"Session-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

    
    def force_question_output(doc_text, max_retries=3):
        base_prompt = f"""
    You are NOT allowed to summarize this document.

    Your task is to ONLY generate exactly 3 due diligence questions based on the document below.

    ❌ Do NOT write an intro or summary.  
    ✅ Each line must start with a number and end with a question mark.

    EXAMPLE FORMAT (and nothing else):
    1. What are the company’s internal controls for AML compliance?
    2. How does the business mitigate regulatory risk across jurisdictions?
    3. What client onboarding procedures are in place to detect fraud?

    📄 DOCUMENT START:
    {doc_text}
    📄 DOCUMENT END.
    """
        for attempt in range(max_retries):
            response = ollama.chat(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": base_prompt}],
                options={"num_predict": 200}
            )
            raw_output = response["message"]["content"].strip()
            questions = re.findall(r"\d\.\s+(.*?\?)", raw_output)

            if len(questions) == 3:
                return questions

        return []

    # === Charger les textes nettoyés disponibles ===
    cleaned_texts_dir = "cleaned_texts"
    cleaned_texts = {
        txt_file: open(txt_file, "r", encoding="utf-8").read()
        for txt_file in glob.glob(f"{cleaned_texts_dir}/*.txt")
    }




    def log_event(user_email, event, details=""):
        db["audit_logs"].insert_one({
            "user": user_email,
            "event": event,
            "details": details,
            "timestamp": datetime.now(timezone.utc)
        })

    def generate_compliance_pdf(session_name, summary, history, red_flags=None, reviewer="Due Diligence Bot"):
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.add_page()

        # --- Title ---
        pdf.set_font("Arial", 'B', 16)
        pdf.cell(0, 10, "Compliance Audit Report", ln=True, align='C')

        pdf.set_font("Arial", '', 12)
        pdf.cell(0, 10, f"Session: {session_name}", ln=True)
        pdf.cell(0, 10, f"Date: {datetime.today().strftime('%Y-%m-%d')}", ln=True)
        pdf.cell(0, 10, f"Reviewer: {reviewer}", ln=True)
        pdf.ln(10)

        # --- Executive Summary ---
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Executive Summary", ln=True)
        pdf.set_font("Arial", '', 12)
        pdf.multi_cell(0, 10, summary)
        pdf.ln(5)

        # --- Red Flags ---
        if red_flags:
            pdf.set_font("Arial", 'B', 14)
            pdf.cell(0, 10, "Red Flags Detected", ln=True)
            pdf.set_font("Arial", '', 12)
            pdf.multi_cell(0, 10, ", ".join(red_flags))
            pdf.ln(5)

        # --- Q&A ---
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Questions & Answers", ln=True)

        for i in range(0, len(history), 2):
            user_msg = history[i]
            bot_msg = history[i+1] if i+1 < len(history) else {"content": "", "tags": []}

            if user_msg["role"] != "user":
                continue

            pdf.set_font("Arial", 'B', 12)
            pdf.multi_cell(0, 10, f"{i//2 + 1}. {user_msg['content']}")
            pdf.set_font("Arial", '', 12)
            pdf.multi_cell(0, 10, bot_msg["content"])

            if bot_msg.get("tags"):
                pdf.set_font("Arial", 'I', 10)
                pdf.cell(0, 8, f"Tags: {', '.join(bot_msg['tags'])}", ln=True)

            pdf.ln(5)

        # --- Signature Section ---
        pdf.set_font("Arial", 'B', 14)
        pdf.cell(0, 10, "Validation & Signature", ln=True)
        pdf.set_font("Arial", '', 12)
        pdf.cell(0, 10, "Signature: ____________________________", ln=True)
        pdf.cell(0, 10, "Date: _________________________________", ln=True)

        # ✅ Export en mémoire compatible Streamlit
        pdf_bytes = pdf.output(dest='S').encode('latin-1')
        pdf_output = BytesIO(pdf_bytes)
        return pdf_output



    # --- Auth utils ---
    def hash_password(password):
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

    def verify_password(password, hashed):
        return bcrypt.checkpw(password.encode(), hashed)

    # --- Auth & Session ---
    if "user" not in st.session_state:
        st.session_state.user = None

    if not st.session_state.user:
        st.subheader("🔐 Login")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        if st.button("Login"):
            user = db["users"].find_one({"first_name": email})

            if user and verify_password(password, user["password"]):
                st.session_state.user = email
                st.success("✅ Logged in as: " + email)
                st.rerun()
            else:
                st.error("❌ Invalid credentials")
        st.stop()

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

    def classify_answer_tags(answer_text):
            prompt = f"""
        You are an AI assistant analyzing answers in a due diligence assistant.

        Based on the following answer, extract **3 to 5 relevant tags** that summarize the key topics or themes discussed.

        🔹 The tags must:
        - Be concise (1–3 words each)
        - Be meaningful (e.g. "KYC", "Digital Assets", "Blockchain Strategy")
        - Not generic ("text", "document", etc.)
        - Not come from a predefined list — generate them based on the content.

        Return in this format only:
        Tags: [tag1, tag2, tag3, ...]


        ANSWER:
        {answer_text}
        """
            response = ollama.chat(
                model=MODEL_NAME,
                messages=[{"role": "user", "content": prompt}],
                options={"num_predict": 150}
            )
            raw = response["message"]["content"].strip()

            # Extraction des tags sous forme de liste
            match = re.search(r"\[([^\]]+)\]", raw)
            if match:
                return [tag.strip() for tag in match.group(1).split(",")]
            return []


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

    # 🔎 Red Flags à surveiller
    def detect_red_flags_with_highlight(text):
        red_flags = [
            "ponzi", "scam", "non audited", "data breach",
            "offshore", "non compliant", "no license",
            "sanction", "money laundering", "anonymous",
            "rug pull", "fraud", "suspicious"
        ]
        
        # Découper le texte en phrases
        sentences = re.split(r'(?<=[.?!])\s+', text)

        matched_flags = set()
        highlighted_sentences = []

        for sentence in sentences:
            original_sentence = sentence
            for flag in red_flags:
                pattern = re.compile(rf'\b({re.escape(flag)})\b', re.IGNORECASE)
                if pattern.search(sentence):
                    sentence = pattern.sub(r'<mark>\1</mark>', sentence)
                    matched_flags.add(flag.lower())
            if sentence != original_sentence:
                highlighted_sentences.append(sentence.strip())

        return sorted(matched_flags), highlighted_sentences

    def evaluate_answer_with_ollama(question, answer):
        prompt = f"""
    You are a senior due diligence reviewer.

    Evaluate the following answer to the question based on:
    - Relevance
    - Completeness
    - Usefulness in due diligence

    Format your response exactly like this:
    Score: X/10  
    Comment: <Your feedback>

    QUESTION:
    {question}

    ANSWER:
    {answer}
    """
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 200}
        )
        result = response["message"]["content"].strip()

        # Extraction du score et du commentaire
        score_match = re.search(r"Score:\s*(\d+)/10", result)
        comment_match = re.search(r"Comment:\s*(.*)", result, re.DOTALL)

        score = int(score_match.group(1)) if score_match else 0
        comment = comment_match.group(1).strip() if comment_match else "No comment."

        return score, comment
    # 📤 PowerPoint Générateur

    def generate_pptx(session_name, summary_text, key_points=None, logo_path=None):
        from pptx import Presentation
        from pptx.util import Inches, Pt
        from pptx.dml.color import RGBColor
        from pptx.enum.text import PP_ALIGN
        from pptx.enum.shapes import MSO_SHAPE
        from io import BytesIO
        from datetime import datetime
        import os

        prs = Presentation()
        prs.slide_width = Inches(13.333)
        prs.slide_height = Inches(7.5)

        COLORS = {
            "dark_blue": RGBColor(18, 32, 47),         # Bleu nuit élégant
            "medium_blue": RGBColor(44, 98, 176),      # Bleu professionnel doux
            "light_blue": RGBColor(173, 208, 240),     # Bleu ciel pâle
            "accent_gold": RGBColor(255, 193, 7),      # Jaune doré vif (accent moderne)
            "dark_gray": RGBColor(33, 37, 41),         # Gris anthracite (texte)
            "light_gray": RGBColor(245, 245, 245),     # Gris très clair (fond)
            "white": RGBColor(255, 255, 255)           # Blanc pur
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
            def add_slide_with_text(text, title="EXECUTIVE SUMMARY"):
                slide = prs.slides.add_slide(prs.slide_layouts[6])
                bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
                bg.fill.solid()
                bg.fill.fore_color.rgb = COLORS["light_gray"]

                header = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12), Inches(1))
                tf = header.text_frame
                p = tf.paragraphs[0]
                run = p.add_run()
                run.text = title
                run.font.size = Pt(32)
                run.font.bold = True
                run.font.color.rgb = COLORS["dark_blue"]

                line = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.5), Inches(1.2), Inches(12), Inches(0.05))
                line.fill.solid()
                line.fill.fore_color.rgb = COLORS["medium_blue"]

                content = slide.shapes.add_textbox(Inches(0.7), Inches(1.5), Inches(12), Inches(5.5))
                tf2 = content.text_frame
                tf2.word_wrap = True
                tf2.clear()

                p = tf2.add_paragraph()
                p.text = text.replace("\n", " ")
                p.font.size = Pt(14)
                p.font.color.rgb = COLORS["dark_gray"]

            chunks = [summary_text[i:i+1200] for i in range(0, len(summary_text), 1200)]
            for i, chunk in enumerate(chunks[:5]):
                add_slide_with_text(chunk, title=f"EXECUTIVE SUMMARY ({i+1})" if len(chunks) > 1 else "EXECUTIVE SUMMARY")

        def add_recommendations_slide():
            slide = prs.slides.add_slide(prs.slide_layouts[6])
            bg = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
            bg.fill.solid()
            bg.fill.fore_color.rgb = COLORS["white"]

            header = slide.shapes.add_textbox(Inches(0.5), Inches(0.4), Inches(12), Inches(1))
            tf = header.text_frame
            p = tf.paragraphs[0]
            run = p.add_run()
            run.text = "KEY RECOMMENDATIONS"
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

        add_title_slide()
        add_summary_slide()
        add_recommendations_slide()

        pptx_io = BytesIO()
        prs.save(pptx_io)
        pptx_io.seek(0)
        return pptx_io

    def render_tags(tags):
        tag_html = ' '.join([
            f'<span style="background-color:#343541;padding:5px 10px;border-radius:12px;color:white;font-size:12px;margin-right:5px;">{tag}</span>'
            for tag in tags
        ])
        st.markdown(tag_html, unsafe_allow_html=True)
    # 💾 Sauvegarde MongoDB

    def save_conversation(session_name, history):
        for msg in history:
            if "tags" not in msg:
                msg["tags"] = []

        collection.update_one(
            {"session": session_name, "user_email": st.session_state.user},
            {
                "$set": {
                    "messages": history,
                    "timestamp": datetime.now(timezone.utc),
                    "user_email": st.session_state.user,
                    "session_title": st.session_state.session_title if "session_title" in st.session_state else session_name
                }
            },
            upsert=True
        )


    def chunk_text(text, max_chars=3000):
        return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]



    # 🔐 INIT SESSION STATE - Avant tout usage
    timestamp_now = datetime.utcnow().strftime('%Y%m%d%H%M%S')
    if "history" not in st.session_state:
        st.session_state.history = []
    if "chat_context" not in st.session_state:
        st.session_state.chat_context = dict(cleaned_texts)
    if "session_name" not in st.session_state:
        st.session_state.session_name = f"Session-{timestamp_now}"

    st.markdown("<h1 style='text-align: center;'>💼 Due Diligence ChatGPT Assistant</h1>", unsafe_allow_html=True)
    if "just_reset" in st.session_state:
        st.toast("🆕 Nouvelle session démarrée.")
        del st.session_state["just_reset"]

    # ➕ Add session info just below the title
    st.markdown(f"<p style='text-align:center; font-size:14px; color:gray;'>🗂️ Session actuelle : <b>{st.session_state.session_name}</b></p>", unsafe_allow_html=True)


    # 📎 Upload document
    st.sidebar.title("📎 Document Context")

    # 📎 Upload multiple documents
    uploaded_files = st.sidebar.file_uploader("Upload .pdf or .txt files", type=["pdf", "txt"], accept_multiple_files=True)
    if uploaded_files:
        st.session_state.chat_context = {}
        for uploaded_file in uploaded_files:
            # ⏱️ Timestamp
            upload_timestamp = datetime.now(timezone.utc)

            # 📥 Sauvegarder temporairement le fichier
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
                tmp.write(uploaded_file.read())
                tmp_path = tmp.name

            # 📄 NLP Pipeline
            raw_text = extract_text_from_pdf(tmp_path)
            cleaned_text = clean_text(raw_text)
            summary = summarize_text(cleaned_text)

            # 💾 Sauvegarde MongoDB
            db["documents"].insert_one({
                "filename": uploaded_file.name,
                "user_email": st.session_state.user,
                "timestamp": upload_timestamp,
                "raw_text": raw_text,
                "cleaned_text": cleaned_text,
                "summary": summary
            })

            log_event(st.session_state.user, "document_upload", f"Parsed and saved {uploaded_file.name}")

            # ➕ Ajouter au contexte de chat
            st.session_state.chat_context[uploaded_file.name] = cleaned_text

            # 🔹 Découpage du document pour questions
            chunks = chunk_text(cleaned_text)

            st.sidebar.subheader(f"💡 Suggested Questions for {uploaded_file.name}")
            for idx, chunk in enumerate(chunks[:1]):  # 1 seul chunk
                with st.spinner(f"Generating questions from chunk {idx+1}..."):
                    result = force_question_output(chunk)

                if not result:
                    st.sidebar.warning(f"❌ No valid questions for {uploaded_file.name}")
                else:
                    for i, question in enumerate(result):
                        if st.sidebar.button(f"❓ {question}", key=f"{uploaded_file.name}_q{i}"):
                            st.session_state["pending_question"] = question

            # 🔍 Analyse red flags
            detected_flags, flagged_sentences = detect_red_flags_with_highlight(cleaned_text)

            if detected_flags:
                st.sidebar.error(f"⚠️ Red flags in {uploaded_file.name}: {', '.join(detected_flags)}")
                with st.sidebar.expander(f"🔍 Sentences in {uploaded_file.name}", expanded=False):
                    for sentence in flagged_sentences:
                        st.sidebar.markdown(f"• {sentence}", unsafe_allow_html=True)
            else:
                st.sidebar.success(f"✅ {uploaded_file.name} loaded without detected risks.")

                        # ➕ Ajouter au contexte de chat
            st.session_state.chat_context[uploaded_file.name] = cleaned_text

            # 💾 Sauvegarder pour Agentic AI
            st.session_state["agentic_file_name"] = uploaded_file.name
            st.session_state["agentic_cleaned_text"] = cleaned_text    
        # Check for the New Chat button and handle session reset
    if st.sidebar.button("➕ New Chat"):
        st.session_state.history = []
        st.session_state.session_name = f"Session-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        st.session_state.chat_context = {
            txt_file: open(txt_file, "r", encoding="utf-8").read()
            for txt_file in glob.glob("cleaned_texts/*.txt")
        }
        st.session_state.selected_session = None  # <=== Important !
        st.session_state["just_reset"] = True
        st.rerun()
    # 💡 Toujours en dehors du bouton
    if "session_title" not in st.session_state:
        st.session_state.session_title = f"My Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"



    st.sidebar.title("🔍 Search in Conversation")

    search_query = st.sidebar.text_input("Enter a keyword...")

    if search_query:
        results = [
            (i, msg) for i, msg in enumerate(st.session_state.history)
            if search_query.lower() in msg.get("content", "").lower()
        ]
        
        if results:
            st.sidebar.success(f"{len(results)} message(s) found.")
            with st.expander("📋 View results"):
                for i, msg in results:
                    role = "👤" if msg["role"] == "user" else "🤖"
                    preview = msg["content"][:100] + ("..." if len(msg["content"]) > 100 else "")
                    st.markdown(f"{role} [{i}] : {preview}")
        else:
            st.sidebar.warning("No matches found.")            

    # 📌 Récupérer tous les tags utilisés
    # 📌 Récupérer tous les tags utilisés par l'utilisateur dans TOUTES les sessions
    all_tags = sorted(set(
        tag
        for session in collection.find({"user_email": st.session_state.user}, {"messages": 1})
        for msg in session.get("messages", [])
        for tag in msg.get("tags", [])
    ))


    st.sidebar.title("🗂️ Filter by Tag")
    selected_tag = st.sidebar.selectbox("Select a tag to filter answers", ["All"] + all_tags)


    # Ensure session state is set up correctly for the first load
    if "history" not in st.session_state:
        st.session_state.history = []
    if "chat_context" not in st.session_state:
        cleaned_texts_dir = "cleaned_texts"
        cleaned_texts = {
            txt_file: open(txt_file, "r", encoding="utf-8").read()
            for txt_file in glob.glob(f"{cleaned_texts_dir}/*.txt")
        }
        st.session_state.chat_context = dict(cleaned_texts)
    if "session_name" not in st.session_state:
        st.session_state.session_name = f"Session-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"








    # 🔄 Chargement des 10 dernières sessions avec titres personnalisés
    chat_sessions = list(
        collection.find(
            {"user_email": st.session_state.user},
            {"session": 1, "session_title": 1, "timestamp": 1}
        ).sort("timestamp", -1).limit(10)
    )

    # 🧠 Mapping session_id → titre (ou session_id si pas de titre)
    session_map = {
        s["session"]: s.get("session_title", s["session"]) for s in chat_sessions
    }

    session_ids = list(session_map.keys())
    session_titles = list(session_map.values())

    # 🧠 Historique des sessions (valeur sélectionnée actuelle)
    if "selected_session" not in st.session_state:
        st.session_state.selected_session = None

    # 📋 Affichage dropdown avec titres
    selected_display = st.sidebar.selectbox(
        "📚 Load a past chat",
        ["Choose an option"] + session_titles,
        index=0 if not st.session_state.selected_session else session_ids.index(st.session_state.selected_session) + 1,
        key="selected_session_display"
    )

    # ✅ Rechargement si changement
    if selected_display != "Choose an option":
        selected_session_id = session_ids[session_titles.index(selected_display)]
        if selected_session_id != st.session_state.session_name:
            doc = collection.find_one({"session": selected_session_id, "user_email": st.session_state.user})
            if doc:
                st.session_state.session_name = selected_session_id
                st.session_state.session_title = doc.get("session_title", selected_session_id)  # Pour affichage cohérent
                st.session_state.history = doc["messages"]
                st.session_state.selected_session = selected_session_id
                st.rerun()



            
       

    # 💬 Chat
    question = st.chat_input("Ask a due diligence question...")
    if question:
        log_event(st.session_state.user, "login")
        log_event(st.session_state.user, "ask_question", question)
        log_event(st.session_state.user, "download_csv", f"session={st.session_state.session_name}")

        # 🔐 Assigner automatiquement un titre de session à partir de la première question
        if len(st.session_state.history) == 0:
            simplified_title = question.strip().capitalize()
            # Nettoyage et troncature
            simplified_title = re.sub(r'[^\w\s-]', '', simplified_title)  # Enlève ponctuation
            if len(simplified_title) > 40:
                simplified_title = simplified_title[:40].rsplit(' ', 1)[0] + "..."
            st.session_state.session_title = simplified_title
            save_conversation(st.session_state.session_name, st.session_state.history)  # Sauvegarde immédiate du titre

        # 🔁 Re-vérifie qu'on est bien sur une nouvelle session (par précaution)
        if "Session-" not in st.session_state.session_name:
            st.session_state.session_name = f"Session-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"

        with st.chat_message("user"):
            st.markdown(question)
        st.session_state.history.append({"role": "user", "content": question})

        with st.spinner("⏳ Thinking..."):
            context = find_relevant_context(question, st.session_state.chat_context)
            answer = generate_answer_with_ollama(question, context)
            tags = classify_answer_tags(answer)
                        # Ajoute la réponse de l'assistant AVEC les tags
            st.session_state.history.append({
                "role": "assistant",
                "content": answer,
                "tags": tags
            })

            if tags:
                st.markdown(f"🏷️ **Tags:** {' '.join([f'`{t}`' for t in tags])}")

st.session_state.history.append({
    "role": "assistant",
    "content": answer,
    "tags": tags
})
        save_conversation(st.session_state.session_name, st.session_state.history)




    def improve_answer_with_ollama(question, old_answer, context):
        prompt = f"""
    You are an expert in Due Diligence.

    The user asked:
    {question}

    An AI assistant gave the following answer:
    "{old_answer}"

    The answer is OK but incomplete. Based on the question and the following CONTEXT, improve and rewrite the answer:
    - Add any missing important points.
    - Be clearer and more actionable.
    - Use complete, professional English.

    CONTEXT:
    {context}

    Now give the improved answer:
    """
        response = ollama.chat(
            model=MODEL_NAME,
            messages=[{"role": "user", "content": prompt}],
            options={"num_predict": 250}
        )
        return response['message']['content'].strip()
    




    # 💬 Affichage messages + Lecture audio + Filtrage par tag (Q&A associés)
    i = 0
    while i < len(st.session_state.history):
        user_msg = st.session_state.history[i]
        assistant_msg = st.session_state.history[i+1] if i+1 < len(st.session_state.history) else None

        # Si filtrage actif et le message assistant ne contient pas le tag → skip
        if selected_tag != "All":
            if not assistant_msg or selected_tag not in assistant_msg.get("tags", []):
                i += 2
                continue

        # Affiche la question
        if user_msg["role"] == "user":
            with st.chat_message("user"):
                st.markdown(user_msg["content"])

        # Affiche la réponse
        if assistant_msg and assistant_msg["role"] == "assistant":
            with st.chat_message("assistant"):
                st.markdown(assistant_msg["content"])

                if assistant_msg.get("tags"):
                    render_tags(assistant_msg["tags"])

                if st.button(f"👍 Like {i}", key=f"like_{i}"):
                    log_event(st.session_state.user, "feedback_like", assistant_msg["content"])

                if st.button(f"🔊 Speak {i}", key=f"speak_{i}"):
                    speak_text(assistant_msg["content"])

                if st.button(f"📈 Evaluate & Improve {i}", key=f"judge_{i}"):
                    user_question = user_msg["content"]
                    score, comment = evaluate_answer_with_ollama(user_question, assistant_msg["content"])
                    st.info(f"🧠 LLM Evaluation:\n\nScore: {score}/10\nComment: {comment}")

                    if score < 7:
                        st.warning("⚠️ The answer can be improved. Generating a refined version...")
                        context = find_relevant_context(user_question, st.session_state.chat_context)
                        improved = improve_answer_with_ollama(user_question, assistant_msg["content"], context)
                        st.markdown("🔁 **Improved Answer:**")
                        st.markdown(improved)

                        tags = classify_answer_tags(improved)
                        st.session_state.history.append({
                            "role": "assistant",
                            "content": improved,
                            "tags": tags
                        })
                        save_conversation(st.session_state.session_name, st.session_state.history)

        i += 2







    use_agentic_ai = st.sidebar.checkbox("🧠 Activer l'Agent de Conformité", value=True)

    if use_agentic_ai and "agentic_cleaned_text" in st.session_state:
        cleaned_text = st.session_state["agentic_cleaned_text"]
        file_name = st.session_state["agentic_file_name"]

        st.sidebar.subheader("🤖 Agent de Conformité Proactif")

        with st.spinner("🔍 Résumé automatique..."):
            summary = summarize_text(cleaned_text)
        st.sidebar.markdown("**📋 Executive Summary:**")
        st.sidebar.markdown(summary)

        # ⚠️ Red Flags
        detected_flags, flagged_sentences = detect_red_flags_with_highlight(cleaned_text)
        if detected_flags:
            st.sidebar.error(f"⚠️ Red Flags détectés : {', '.join(detected_flags)}")
            with st.sidebar.expander("🔎 Détails"):
                for s in flagged_sentences:
                    st.sidebar.markdown(f"• {s}", unsafe_allow_html=True)
        else:
            st.sidebar.success("✅ Aucun signal critique détecté.")

        # ❓ Questions automatiques
        auto_questions = force_question_output(cleaned_text)
        if auto_questions:
            st.sidebar.markdown("**💡 Questions Générées par l'Agent :**")
            for i, q in enumerate(auto_questions):
                st.sidebar.markdown(f"**{i+1}.** {q}")

                with st.spinner("💬 Génération de réponse..."):
                    context = find_relevant_context(q, {file_name: cleaned_text})
                    answer = generate_answer_with_ollama(q, context)
                    score, comment = evaluate_answer_with_ollama(q, answer)

                    st.sidebar.markdown(f"🔹 **Réponse :** {answer}")
                    st.sidebar.markdown(f"📊 **Évaluation :** {score}/10")
                    st.sidebar.markdown(f"📝 **Commentaire :** {comment}")

                    # 💾 Ajout dans l'historique
                    st.session_state.history.append({
                        "role": "user",
                        "content": q,
                        "tags": [],
                    })
                    st.session_state.history.append({
                        "role": "assistant",
                        "content": answer,
                        "tags": classify_answer_tags(answer),
                    })




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


    if st.sidebar.button("📄 Export PDF Report"):
        if st.session_state.chat_context and st.session_state.history:
            raw_doc_text = list(st.session_state.chat_context.values())[0]
            summary = summarize_text(raw_doc_text)
            red_flags, _ = detect_red_flags_with_highlight(raw_doc_text)

            pdf_file = generate_compliance_pdf(
                session_name=st.session_state.session_name,
                summary=summary,
                history=st.session_state.history,
                red_flags=red_flags
            )

            st.sidebar.download_button(
                label="⬇️ Télécharger le rapport PDF",
                data=pdf_file,
                file_name=f"{st.session_state.session_name}_rapport.pdf",
                mime="application/pdf"
            )

    st.sidebar.markdown("---")
    email_username = st.session_state.user.split("@")[0]
    st.sidebar.write(f"👤 Logged in as:**{email_username}** ")
    if st.sidebar.button("🚪 Logout"):
            st.session_state.user = None
            st.rerun()             
       
