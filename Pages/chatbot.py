import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import torch
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import json
from model import model, tokenizer
import base64
import io
from PyPDF2 import PdfReader
from docx import Document
import datetime
from pymongo import MongoClient
from flask import session
import os
from io import BytesIO
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.dml.color import RGBColor
from pptx.oxml.xmlchemy import OxmlElement

dash.register_page(__name__, path="/banque_reponse", name="AI Chatbot")

theme_color = "#00eaff"

# Initialisation MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["due_diligence_db"]

# Chargement FAISS + embeddings
try:
    index = faiss.read_index("faiss_index.bin")
    chunks = np.load("text_chunks.npy", allow_pickle=True).tolist()
except:
    index = None
    chunks = []
embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Banque de questions
try:
    with open("question_bank_with_answers.json", "r", encoding="utf-8") as f:
        question_bank = json.load(f)
except FileNotFoundError:
    question_bank = {"ESG": [], "Compliance": [], "Legal": []}

# Fonctions utilitaires
def extract_text_from_file(filename, content):
    content_type, content_string = content.split(',')
    decoded = base64.b64decode(content_string)
    
    if filename.lower().endswith('.pdf'):
        try:
            pdf_reader = PdfReader(io.BytesIO(decoded))
            return "".join(page.extract_text() or "" for page in pdf_reader.pages)
        except:
            return ""
    elif filename.lower().endswith('.docx'):
        try:
            doc = Document(io.BytesIO(decoded))
            return "\n".join(paragraph.text for paragraph in doc.paragraphs)
        except:
            return ""
    elif filename.lower().endswith('.txt'):
        try:
            return decoded.decode('utf-8')
        except:
            return ""
    return ""

def chunk_text(text, chunk_size=500):
    return [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]

def find_answer_in_bank(query):
    for category in question_bank:
        for entry in question_bank[category]:
            if query.lower() in entry["question"].lower():
                return entry["answer"]
    return None

def retrieve_text(query, user_id, top_k=1):
    query_embedding = embed_model.encode([query], convert_to_numpy=True)
    combined_context = []

    if index is not None:
        try:
            distances, indices = index.search(query_embedding, top_k)
            combined_context.extend([chunks[i] for i in indices[0] if i >= 0])
        except:
            pass

    if user_id:
        for doc in db["user_documents"].find({"user_id": user_id}):
            if "index_file" in doc and os.path.exists(doc["index_file"]):
                try:
                    doc_index = faiss.read_index(doc["index_file"])
                    doc_chunks = np.load(doc["chunks_file"], allow_pickle=True).tolist()
                    distances, indices = doc_index.search(query_embedding, top_k)
                    combined_context.extend([doc_chunks[i] for i in indices[0] if i >= 0])
                except:
                    continue

    return "\n".join(combined_context)

def generate_rag_response(query):
    user_id = session.get("user_id", None)
    
    answer_from_bank = find_answer_in_bank(query)
    if answer_from_bank:
        if user_id:
            db["conversations"].insert_one({
                "user_id": user_id,
                "question": query,
                "answer": answer_from_bank,
                "timestamp": datetime.datetime.utcnow(),
                "source": "question_bank"
            })
        return html.Div([
            html.Div("Réponse trouvée dans la banque :", style={"fontWeight": "bold", "color": theme_color}),
            html.Div(answer_from_bank, style={"marginTop": "10px"})
        ])
    
    context = retrieve_text(query, user_id)
    if not context:
        answer = "Aucune information pertinente trouvée. Veuillez uploader des documents ou poser une question générale."
        if user_id:
            db["conversations"].insert_one({
                "user_id": user_id,
                "question": query,
                "answer": answer,
                "timestamp": datetime.datetime.utcnow(),
                "source": "no_context"
            })
        return html.Div(answer, style={"color": "#ff5555"})

    full_query = f"Context: {context}\n\nQuestion: {query}"
    inputs = tokenizer(full_query, return_tensors="pt", truncation=True, max_length=2048).to("cuda" if torch.cuda.is_available() else "cpu")
    output = model.generate(**inputs, max_new_tokens=200)
    decoded = tokenizer.decode(output[0], skip_special_tokens=True)

    sections = {"Context": "", "Question": "", "Answer": ""}
    for line in decoded.split("\n"):
        if line.strip().startswith("Context:"):
            sections["Context"] = line.replace("Context:", "").strip()
        elif line.strip().startswith("Question:"):
            sections["Question"] = line.replace("Question:", "").strip()
        elif line.strip().startswith("Answer:"):
            sections["Answer"] = line.replace("Answer:", "").strip()
        else:
            sections["Answer"] += line.strip() + " "

    if not sections["Answer"].strip():
        sections["Answer"] = "Désolé, je n'ai pas pu générer une réponse claire. Essayez de reformuler."

    if user_id:
        db["conversations"].insert_one({
            "user_id": user_id,
            "question": query,
            "answer": sections["Answer"],
            "timestamp": datetime.datetime.utcnow(),
            "source": "documents"
        })

    return html.Div([
        html.Div("Context :", style={"fontWeight": "bold", "color": theme_color}),
        html.Div(sections["Context"], style={"marginBottom": "10px"}),
        html.Div("Question :", style={"fontWeight": "bold", "color": theme_color}),
        html.Div(sections["Question"], style={"marginBottom": "10px"}),
        html.Div("Réponse :", style={"fontWeight": "bold", "color": theme_color}),
        html.Div(sections["Answer"])
    ])

# Fonction pour appliquer un fond sombre à une diapositive
def set_slide_background(slide):
    background = slide.background
    fill = background.fill
    fill.solid()
    fill.fore_color.rgb = RGBColor(10, 20, 40)  # Fond bleu foncé

# Fonction pour générer une présentation PPTX stylisée
def generate_pptx(user_id):
    if not user_id:
        return None

    # Créer une nouvelle présentation
    prs = Presentation()
    prs.slide_width = Inches(16)  # Format 16:9 pour un look moderne
    prs.slide_height = Inches(9)

    # Slide 1 : Introduction
    slide_layout = prs.slide_layouts[0]  # Layout pour titre
    slide = prs.slides.add_slide(slide_layout)
    set_slide_background(slide)
    title = slide.shapes.title
    subtitle = slide.placeholders[1]
    title.text = "Due Diligence Report"
    title.text_frame.paragraphs[0].font.size = Pt(44)
    title.text_frame.paragraphs[0].font.color.rgb = RGBColor(0, 234, 255)  # Cyan
    title.text_frame.paragraphs[0].font.bold = True
    subtitle.text = "Prepared by Chainvestor Hub AI Chatbot\n" + f"Generated on {datetime.datetime.now().strftime('%Y-%m-%d')}"
    subtitle.text_frame.paragraphs[0].font.size = Pt(20)
    subtitle.text_frame.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)  # Blanc

    # Slide 2 : Résumé des documents uploadés
    slide_layout = prs.slide_layouts[1]  # Layout pour titre + contenu
    slide = prs.slides.add_slide(slide_layout)
    set_slide_background(slide)
    title = slide.shapes.title
    title.text = "Uploaded Documents Overview"
    title.text_frame.paragraphs[0].font.size = Pt(32)
    title.text_frame.paragraphs[0].font.color.rgb = RGBColor(0, 234, 255)  # Cyan
    title.text_frame.paragraphs[0].font.bold = True

    content = slide.placeholders[1].text_frame
    content.text = "Summary of uploaded documents:\n"
    content.paragraphs[0].font.size = Pt(18)
    content.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)  # Blanc

    documents = db["user_documents"].find({"user_id": user_id})
    doc_count = db["user_documents"].count_documents({"user_id": user_id})
    if doc_count == 0:
        p = content.add_paragraph()
        p.text = "No documents uploaded."
        p.font.size = Pt(14)
        p.font.color.rgb = RGBColor(255, 85, 85)  # Rouge clair
    else:
        for doc in documents:
            filename = doc.get("filename", "Unknown")
            content_text = doc.get("content", "")[:300] + "..." if len(doc.get("content", "")) > 300 else doc.get("content", "")
            # Titre du document
            p = content.add_paragraph()
            p.text = f"📄 {filename}"
            p.font.size = Pt(16)
            p.font.color.rgb = RGBColor(0, 234, 255)  # Cyan
            p.font.bold = True
            # Résumé
            p = content.add_paragraph()
            p.text = f"Summary: {content_text}"
            p.font.size = Pt(14)
            p.font.color.rgb = RGBColor(200, 200, 200)  # Gris clair
            p.space_after = Pt(10)

    # Slide 3 : Questions et réponses
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    set_slide_background(slide)
    title = slide.shapes.title
    title.text = "Key Questions & Answers"
    title.text_frame.paragraphs[0].font.size = Pt(32)
    title.text_frame.paragraphs[0].font.color.rgb = RGBColor(0, 234, 255)  # Cyan
    title.text_frame.paragraphs[0].font.bold = True

    content = slide.placeholders[1].text_frame
    content.text = "Recent interactions with the AI Chatbot:\n"
    content.paragraphs[0].font.size = Pt(18)
    content.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)  # Blanc

    conversations = db["conversations"].find({"user_id": user_id}).sort("timestamp", -1).limit(3)  # 3 dernières conversations pour éviter surcharge
    conv_count = db["conversations"].count_documents({"user_id": user_id})
    if conv_count == 0:
        p = content.add_paragraph()
        p.text = "No conversations recorded."
        p.font.size = Pt(14)
        p.font.color.rgb = RGBColor(255, 85, 85)  # Rouge clair
    else:
        for conv in conversations:
            question = conv.get("question", "N/A")
            answer = conv.get("answer", "N/A")[:200] + "..." if len(conv.get("answer", "N/A")) > 200 else conv.get("answer", "N/A")
            # Question
            p = content.add_paragraph()
            p.text = f"❓ {question}"
            p.font.size = Pt(16)
            p.font.color.rgb = RGBColor(0, 234, 255)  # Cyan
            p.font.bold = True
            # Réponse
            p = content.add_paragraph()
            p.text = f"Answer: {answer}"
            p.font.size = Pt(14)
            p.font.color.rgb = RGBColor(200, 200, 200)  # Gris clair
            p.space_after = Pt(10)

    # Slide 4 : Conclusion
    slide_layout = prs.slide_layouts[1]
    slide = prs.slides.add_slide(slide_layout)
    set_slide_background(slide)
    title = slide.shapes.title
    title.text = "Conclusion"
    title.text_frame.paragraphs[0].font.size = Pt(32)
    title.text_frame.paragraphs[0].font.color.rgb = RGBColor(0, 234, 255)  # Cyan
    title.text_frame.paragraphs[0].font.bold = True

    content = slide.placeholders[1].text_frame
    content.text = "Thank you for using Chainvestor Hub AI Chatbot!\n"
    content.paragraphs[0].font.size = Pt(18)
    content.paragraphs[0].font.color.rgb = RGBColor(255, 255, 255)  # Blanc

    p = content.add_paragraph()
    p.text = f"Total Documents Analyzed: {doc_count}\nTotal Questions Answered: {conv_count}"
    p.font.size = Pt(16)
    p.font.color.rgb = RGBColor(200, 200, 200)  # Gris clair

    p = content.add_paragraph()
    p.text = "For more insights, visit our platform."
    p.font.size = Pt(14)
    p.font.color.rgb = RGBColor(0, 234, 255)  # Cyan
    p.font.italic = True

    # Sauvegarder la présentation dans un buffer
    buffer = BytesIO()
    prs.save(buffer)
    buffer.seek(0)

    # Encoder en base64 pour le téléchargement
    pptx_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")
    return pptx_base64

# === Layout ===
chat_history = []

layout = html.Div([
    html.Div([
        html.H2("💬 AI Chatbot", style={
            "color": "#00eaff",
            "textAlign": "center",
            "marginTop": "40px",
            "fontSize": "2.5em",
            "textShadow": "0 0 10px #00eaff"
        }),

        # Upload pour les utilisateurs
        dcc.Upload(
            id="user-upload",
            children=html.Div([
                "Glisser-déposer ou ",
                html.A("Sélectionner des documents (PDF, DOCX, TXT)")
            ]),
            style={
                "width": "70%",
                "height": "60px",
                "lineHeight": "60px",
                "borderWidth": "2px",
                "borderStyle": "dashed",
                "borderRadius": "12px",
                "textAlign": "center",
                "margin": "20px auto",
                "color": "#ffffff",
                "borderColor": theme_color,
                "background": "rgba(255,255,255,0.05)",
                "backdropFilter": "blur(6px)"
            },
            multiple=True
        ),
        dcc.Loading(
            id="upload-loading",
            type="dot",
            color=theme_color,
            children=html.Div(id="user-upload-status", style={"color": "#ffffff", "textAlign": "center"})
        ),
        html.Div(id="uploaded-files-list", style={"color": "#ffffff", "margin": "10px auto", "textAlign": "center"}),

        # Bouton pour effacer les uploads
        dbc.Button("Effacer les documents", id="clear-upload-button", n_clicks=0, style={
            "backgroundColor": "#ff5555",
            "border": "none",
            "color": "#ffffff",
            "padding": "12px 30px",
            "fontWeight": "bold",
            "borderRadius": "10px",
            "boxShadow": "0 0 12px #ff5555",
            "margin": "10px auto",
            "display": "block"
        }),

        # Bouton pour générer la présentation PPTX
        dbc.Button("Générer une présentation PPTX", id="generate-pptx-button", n_clicks=0, style={
            "backgroundColor": "#00ff00",
            "border": "none",
            "color": "#000000",
            "padding": "12px 30px",
            "fontWeight": "bold",
            "borderRadius": "10px",
            "boxShadow": "0 0 12px #00ff00",
            "margin": "10px auto",
            "display": "block"
        }),
        html.Div(id="pptx-download-link", style={"textAlign": "center", "margin": "10px auto"}),
        dcc.Download(id="download-pptx"),

        html.Div(id="chat-container", children=chat_history, style={
            "width": "70%",
            "height": "60vh",
            "margin": "30px auto",
            "padding": "20px",
            "background": "rgba(0,0,0,0.3)",
            "borderRadius": "16px",
            "overflowY": "auto",
            "boxShadow": "0 0 15px #00eaff",
            "backdropFilter": "blur(10px)",
            "color": "#fff",
            "display": "flex",
            "flexDirection": "column",
        }),

        html.Div([
            dcc.Input(id="input-box", type="text", placeholder="Posez votre question...",
                      style={
                          "width": "70%",
                          "padding": "15px",
                          "fontSize": "1.1em",
                          "border": f"2px solid {theme_color}",
                          "borderRadius": "12px",
                          "background": "rgba(255,255,255,0.05)",
                          "color": "#ffffff",
                          "backdropFilter": "blur(6px)",
                          "marginRight": "15px",
                      }),
            dbc.Button("Envoyer", id="submit-button", n_clicks=0, style={
                "padding": "12px 30px",
                "fontWeight": "bold",
                "fontSize": "1em",
                "backgroundColor": theme_color,
                "border": "none",
                "borderRadius": "10px",
                "boxShadow": "0 0 12px #00eaff",
                "color": "#000"
            }),
        ], style={"textAlign": "center", "marginBottom": "40px"}),

        dcc.Loading(id="loading", type="dot", color=theme_color, children=html.Div(id="loading-output")),
        dcc.Store(id="user-chunks-store", storage_type="session", data=[])
    ])
], style={
    "minHeight": "100vh",
    "backgroundImage": "url('/assets/your-background.jpg')",
    "backgroundSize": "cover",
    "backgroundPosition": "center",
    "padding": "20px"
})

# === Callbacks ===
@dash.callback(
    [Output("user-upload-status", "children"),
     Output("user-chunks-store", "data"),
     Output("uploaded-files-list", "children")],
    Input("user-upload", "filename"),
    Input("user-upload", "contents"),
    State("user-chunks-store", "data"),
    prevent_initial_call=True
)
def manage_user_upload(filenames, contents, stored_chunks):
    if not filenames or not contents:
        return "Veuillez uploader un document pour commencer.", stored_chunks, "Aucun document uploadé."

    user_id = session.get("user_id", None)
    if not user_id:
        return "Veuillez vous connecter pour uploader des documents.", stored_chunks, "Aucun document uploadé."

    all_chunks = stored_chunks if stored_chunks else []
    uploaded_files = []

    for filename, content in zip(filenames, contents):
        if not filename.lower().endswith(('.pdf', '.docx', '.txt')):
            return f"Type de fichier invalide : {filename}", stored_chunks, dash.no_update
        content_type, content_string = content.split(',')
        if len(content_string) > 5_000_000:  # Limite à 5MB
            return f"Fichier trop volumineux : {filename}", stored_chunks, dash.no_update

        try:
            text = extract_text_from_file(filename, content)
            if not text.strip():
                return f"Impossible d'extraire le texte de {filename}.", stored_chunks, dash.no_update
            new_chunks_from_file = chunk_text(text)[:100]  # Limite à 100 chunks
            all_chunks.extend(new_chunks_from_file)
            uploaded_files.append(filename)

            # Stocker dans MongoDB
            doc_id = db["user_documents"].insert_one({
                "filename": filename,
                "content": text,
                "chunks": new_chunks_from_file,
                "user_id": user_id,
                "uploaded_at": datetime.datetime.utcnow()
            }).inserted_id

            # Créer et sauvegarder l'index FAISS
            embeddings = embed_model.encode(new_chunks_from_file, convert_to_numpy=True)
            dimension = embeddings.shape[1]
            file_index = faiss.IndexFlatL2(dimension)
            file_index.add(embeddings)
            faiss.write_index(file_index, f"faiss_index_user_{doc_id}.bin")
            np.save(f"text_chunks_user_{doc_id}.npy", np.array(new_chunks_from_file, dtype=object))

            db["user_documents"].update_one(
                {"_id": doc_id},
                {"$set": {
                    "index_file": f"faiss_index_user_{doc_id}.bin",
                    "chunks_file": f"text_chunks_user_{doc_id}.npy"
                }}
            )

        except Exception as e:
            return f"Erreur lors du traitement de {filename} : {str(e)}", stored_chunks, dash.no_update

    return (f"{len(filenames)} document(s) uploadé(s) avec succès. Prêt à répondre aux questions.",
            all_chunks,
            html.Ul([html.Li(f) for f in uploaded_files]))

@dash.callback(
    [Output("user-chunks-store", "data", allow_duplicate=True),
     Output("user-upload-status", "children", allow_duplicate=True),
     Output("uploaded-files-list", "children", allow_duplicate=True)],
    Input("clear-upload-button", "n_clicks"),
    prevent_initial_call=True
)
def clear_uploads(n_clicks):
    user_id = session.get("user_id", None)
    if user_id:
        for doc in db["user_documents"].find({"user_id": user_id}):
            for file_key in ["index_file", "chunks_file"]:
                file_path = doc.get(file_key, "")
                if file_path and os.path.exists(file_path):
                    os.remove(file_path)
        db["user_documents"].delete_many({"user_id": user_id})
    return [], "Aucun document uploadé.", "Aucun document uploadé."

@dash.callback(
    Output("chat-container", "children"),
    Output("loading-output", "children"),
    Output("input-box", "value"),
    Input("submit-button", "n_clicks"),
    State("input-box", "value"),
    prevent_initial_call=True
)
def update_chat(n_clicks, message):
    global chat_history

    if not message:
        return chat_history, "", ""

    chat_history.append(
        html.Div(message, style={
            "alignSelf": "flex-end",
            "backgroundColor": "#00eaff",
            "color": "#000",
            "padding": "12px 20px",
            "borderRadius": "16px",
            "marginBottom": "10px",
            "maxWidth": "70%",
            "boxShadow": "0 0 8px #00eaff",
            "fontWeight": "bold",
        })
    )

    chat_history.append(
        html.Div("...", style={
            "alignSelf": "flex-start",
            "backgroundColor": "rgba(255,255,255,0.1)",
            "padding": "12px 20px",
            "borderRadius": "16px",
            "marginBottom": "10px",
            "maxWidth": "70%",
            "boxShadow": "0 0 8px #00eaff",
            "fontStyle": "italic"
        })
    )

    children_so_far = chat_history.copy()

    ai_response = generate_rag_response(message)

    chat_history = chat_history[:-1]
    chat_history.append(
        html.Div(ai_response, style={
            "alignSelf": "flex-start",
            "backgroundColor": "rgba(255,255,255,0.1)",
            "padding": "12px 20px",
            "borderRadius": "16px",
            "marginBottom": "10px",
            "maxWidth": "70%",
            "boxShadow": "0 0 8px #00eaff",
        })
    )

    return chat_history, "", ""

# Callback pour générer et télécharger la présentation PPTX
@dash.callback(
    [Output("pptx-download-link", "children"),
     Output("download-pptx", "data")],
    Input("generate-pptx-button", "n_clicks"),
    prevent_initial_call=True
)
def generate_and_download_pptx(n_clicks):
    user_id = session.get("user_id", None)
    if not user_id:
        return html.Div("Veuillez vous connecter pour générer une présentation.", style={"color": "#ff5555"}), None

    pptx_base64 = generate_pptx(user_id)
    if not pptx_base64:
        return html.Div("Aucune donnée disponible pour générer une présentation.", style={"color": "#ff5555"}), None

    download_link = html.A(
        "Télécharger la présentation PPTX",
        href=f"data:application/vnd.openxmlformats-officedocument.presentationml.presentation;base64,{pptx_base64}",
        download="due_diligence_report.pptx",
        style={
            "color": theme_color,
            "fontWeight": "bold",
            "textDecoration": "underline"
        }
    )

    return download_link, dict(
        content=pptx_base64,
        filename="due_diligence_report.pptx",
        type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
        base64=True
    )