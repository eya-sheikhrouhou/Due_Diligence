import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
import torch
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

dash.register_page(__name__, path="/chatbot")

theme_color = "#00eaff"

# Charger le modèle avec optimisation
bnb_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.float16,
    bnb_4bit_use_double_quant=True,
)
model_name = "mistralai/Mistral-7B-Instruct-v0.1"
tokenizer = AutoTokenizer.from_pretrained(model_name)
model = AutoModelForCausalLM.from_pretrained(model_name, quantization_config=bnb_config, device_map="auto")

# Charger la carte et les morceaux
index = faiss.read_index("faiss_index.bin")
chunks = np.load("text_chunks.npy", allow_pickle=True).tolist()
embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Chercher les morceaux pertinents
def retrieve_text(query, top_k=1):
    query_embedding = embed_model.encode([query], convert_to_numpy=True)
    distances, indices = index.search(query_embedding, top_k)
    retrieved_texts = [chunks[i] for i in indices[0]]
    return "\n".join(retrieved_texts)

# Générer une réponse
def generate_rag_response(query):
    retrieved_context = retrieve_text(query)
    full_query = f"Context: {retrieved_context}\n\nQuestion: {query}"
    inputs = tokenizer(full_query, return_tensors="pt", truncation=True, max_length=2048).to("cuda" if torch.cuda.is_available() else "cpu")
    output = model.generate(**inputs, max_new_tokens=200)
    return tokenizer.decode(output[0], skip_special_tokens=True)

# Mise en page du chatbot en anglais
layout = html.Div([
    html.H2("AI Chatbot", style={
        "fontSize": "3em",
        "fontWeight": "700",
        "color": "#ffffff",
        "textAlign": "center",
        "marginTop": "100px",
        "opacity": "0",
        "animation": "fadeIn 1s ease forwards"
    }),
    dcc.Input(
        id="input-box",
        type="text",
        placeholder="Ask your question...",
        style={
            "width": "50%",
            "padding": "12px",
            "fontSize": "1.1em",
            "border": f"1px solid {theme_color}",
            "borderRadius": "5px",
            "background": "rgba(10, 10, 10, 0.8)",
            "color": "#ffffff",
            "display": "block",
            "margin": "30px auto",
            "boxShadow": f"0 0 10px {theme_color}",
            "transition": "all 0.3s ease"
        }
    ),
    dbc.Button("Send", id="submit-button", n_clicks=0, style={
        "background": theme_color,
        "border": "none",
        "color": "#0a0a0a",
        "padding": "10px 30px",
        "fontSize": "1.1em",
        "fontWeight": "700",
        "display": "block",
        "margin": "0 auto",
        "boxShadow": f"0 0 10px {theme_color}",
        "animation": "pulse 2s infinite",
        "borderRadius": "25px"
    }),
    html.Div(id="output-box", style={
        "marginTop": "40px",
        "width": "60%",
        "padding": "15px",
        "background": "rgba(10, 10, 10, 0.8)",
        "border": f"1px solid {theme_color}",
        "borderRadius": "5px",
        "color": "#ffffff",
        "margin": "0 auto",
        "boxShadow": f"0 0 10px {theme_color}",
        "opacity": "0",
        "animation": "fadeIn 0.5s ease forwards"
    })
])

# Logique de mise à jour
@dash.callback(
    Output("output-box", "children"),
    [Input("submit-button", "n_clicks")],
    [State("input-box", "value")]
)
def update_output(n_clicks, value):
    if n_clicks > 0 and value:
        response = generate_rag_response(value)
        return html.P(response)
    return "Ask a question to start."