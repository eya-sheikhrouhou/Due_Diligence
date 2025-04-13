import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import torch
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import json
from model import model, tokenizer

dash.register_page(__name__, path="/banque_reponse", name="AI Chatbot")

theme_color = "#00eaff"

# Chargement FAISS + embeddings
index = faiss.read_index("faiss_index.bin")
chunks = np.load("text_chunks.npy", allow_pickle=True).tolist()
embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Banque de questions
try:
    with open("question_bank_with_answers.json", "r", encoding="utf-8") as f:
        question_bank = json.load(f)
except FileNotFoundError:
    question_bank = {"ESG": [], "Compliance": [], "Legal": []}

def find_answer_in_bank(query):
    for category in question_bank:
        for entry in question_bank[category]:
            if query.lower() in entry["question"].lower():
                return entry["answer"]
    return None

def retrieve_text(query, top_k=1):
    query_embedding = embed_model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_embedding, top_k)
    return "\n".join([chunks[i] for i in indices[0]])

def generate_rag_response(query):
    answer_from_bank = find_answer_in_bank(query)
    if answer_from_bank:
        return answer_from_bank
    context = retrieve_text(query)
    full_query = f"Context: {context}\n\nQuestion: {query}"
    inputs = tokenizer(full_query, return_tensors="pt", truncation=True, max_length=2048).to("cuda" if torch.cuda.is_available() else "cpu")
    output = model.generate(**inputs, max_new_tokens=200)
    decoded = tokenizer.decode(output[0], skip_special_tokens=True)
    return decoded

# === Layout ===
layout = html.Div([
    html.Div([
        html.H2("💬 AI Chatbot", style={
            "color": "#00eaff",
            "textAlign": "center",
            "marginTop": "40px",
            "fontSize": "2.5em",
            "textShadow": "0 0 10px #00eaff"
        }),

        html.Div(id="chat-container", children=[], style={
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
            dcc.Input(id="input-box", type="text", placeholder="Ask your question...",
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

        dcc.Loading(id="loading", type="dot", color=theme_color, children=html.Div(id="loading-output"))
    ])
], style={
    "minHeight": "100vh",
    "backgroundImage": "url('/assets/your-background.jpg')",
    "backgroundSize": "cover",
    "backgroundPosition": "center",
    "padding": "20px"
})

# === Callback ===
chat_history = []

@dash.callback(
    Output("chat-container", "children"),
    Output("loading-output", "children"),
    Output("input-box", "value"),  # Pour vider le champ
    Input("submit-button", "n_clicks"),
    State("input-box", "value"),
    prevent_initial_call=True
)
def update_chat(n_clicks, message):
    global chat_history

    if not message:
        return chat_history, "", ""

    # Message utilisateur
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

    # Message en chargement "..."
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

    # Refresh UI pour afficher les messages avec les "..."
    children_so_far = chat_history.copy()

    # Génère réponse
    ai_response = generate_rag_response(message)

    # Retire "..." et remplace par la vraie réponse
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
