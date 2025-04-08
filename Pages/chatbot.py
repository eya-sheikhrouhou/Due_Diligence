import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import torch
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import json
from model import model, tokenizer  # Importer le modèle et le tokenizer depuis model.py

dash.register_page(__name__, path="/banque_reponse", name="Chatbot")

theme_color = "#00eaff"

# Chargement FAISS + embeddings
index = faiss.read_index("faiss_index.bin")
chunks = np.load("text_chunks.npy", allow_pickle=True).tolist()
embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Charger la banque de questions/réponses
try:
    with open("question_bank_with_answers.json", "r", encoding="utf-8") as f:
        question_bank = json.load(f)
except FileNotFoundError:
    question_bank = {"ESG": [], "Compliance": [], "Legal": []}

# Fonction pour chercher une réponse dans la banque
def find_answer_in_bank(query):
    for category in question_bank:
        for entry in question_bank[category]:
            if query.lower() in entry["question"].lower():  # Recherche simple par correspondance
                return entry["answer"]
    return None

# RAG pour générer des réponses si la question n'est pas dans la banque
def retrieve_text(query, top_k=1):
    query_embedding = embed_model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_embedding, top_k)
    return "\n".join([chunks[i] for i in indices[0]])

def generate_rag_response(query):
    # Chercher d'abord dans la banque de questions/réponses
    answer_from_bank = find_answer_in_bank(query)
    if answer_from_bank:
        return format_response_with_highlights(answer_from_bank)
    
    # Sinon, générer une réponse avec Mistral
    context = retrieve_text(query)
    full_query = f"Context: {context}\n\nQuestion: {query}"
    inputs = tokenizer(full_query, return_tensors="pt", truncation=True, max_length=2048).to("cuda" if torch.cuda.is_available() else "cpu")
    output = model.generate(**inputs, max_new_tokens=200)
    decoded = tokenizer.decode(output[0], skip_special_tokens=True)
    return format_response_with_highlights(decoded)

def format_response_with_highlights(response):
    sentences = response.split(". ")
    highlighted = []
    highlight_color = "#00eaff"
    keywords = ["legal", "rights", "property", "recognition", "not available", "key", "important", "main", "crucial"]

    for sentence in sentences:
        if any(keyword in sentence.lower() for keyword in keywords):
            highlighted.append(html.Span(sentence, style={"color": highlight_color, "fontWeight": "bold"}))
        else:
            highlighted.append(sentence)
        if sentence != sentences[-1]:
            highlighted.append(". ")
    return highlighted

# Layout
layout = html.Div([
    html.Div([
        html.H2("AI Chatbot", style={
            "fontSize": "2.8em",
            "fontWeight": "bold",
            "textAlign": "center",
            "marginTop": "60px",
            "color": "#ffffff",
            "textShadow": "0 0 8px #00eaff"
        }),

        # Zone de texte avec taille fixe
        html.Div(id="output-box", style={
            "margin": "20px auto",
            "width": "65%",
            "height": "300px",  # Fixe la hauteur pour l'output
            "padding": "20px",
            "background": "transparent",
            "border": f"1px solid {theme_color}",
            "borderRadius": "12px",
            "color": "#ffffff",
            "boxShadow": f"0 0 12px {theme_color}",
            "backdropFilter": "blur(6px)",
            "overflowY": "auto",  # Ajoute un scroll vertical si nécessaire
        }),

        html.Div([
            dcc.Input(
                id="input-box",
                type="text",
                placeholder="Ask your question...",
                style={
                    "width": "65%",
                    "height": "50px",  # Hauteur fixée pour l'input
                    "padding": "12px",
                    "fontSize": "1.1em",
                    "border": f"1px solid {theme_color}",
                    "borderRadius": "8px",
                    "color": "#ffffff",
                    "background": "transparent",
                    "backdropFilter": "blur(6px)",
                    "boxShadow": f"0 0 6px {theme_color}"
                }
            ),
            dbc.Button("Send", id="submit-button", n_clicks=0, style={
                "backgroundColor": theme_color,
                "border": "none",
                "color": "#0a0a0a",
                "padding": "10px 25px",
                "fontWeight": "bold",
                "borderRadius": "8px",
                "boxShadow": f"0 0 10px {theme_color}"
            }),
        ], style={"textAlign": "center", "marginTop": "25px", "marginBottom": "50px"}),

        dcc.Loading(
            id="loading-response",
            type="circle",
            color=theme_color,
            children=html.Div(id="loading-output")
        )
    ])
], style={
    "minHeight": "100vh",
    "padding": "30px",
    "backgroundImage": "url('/assets/your-background.jpg')",
    "backgroundSize": "cover",
    "backgroundPosition": "center",
    "display": "flex",
    "flexDirection": "column",
    "alignItems": "center"
})

# Callback
@dash.callback(
    Output("output-box", "children"),
    Output("loading-output", "children"),
    Input("submit-button", "n_clicks"),
    State("input-box", "value")
)
def update_output(n_clicks, value):
    if n_clicks > 0 and value:
        response = generate_rag_response(value)
        return html.P(response), ""
    return "", ""