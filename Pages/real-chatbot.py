import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
from chatterbot import ChatBot
from chatterbot.trainers import ChatterBotCorpusTrainer

dash.register_page(__name__, path="/real-chatbot", name="Real Chatbot")

theme_color = "#00eaff"

# Configurer ChatterBot avec une base de données persistante
chatbot = ChatBot(
    "CryptoBot",
    storage_adapter="chatterbot.storage.SQLStorageAdapter",  # Utilise SQLite
    database_uri="sqlite:///database.sqlite3"  # Base de données SQLite
)

# Entraîner le chatbot uniquement si nécessaire
trainer = ChatterBotCorpusTrainer(chatbot)
try:
    trainer.train("chatterbot.corpus.english.greetings")  # Corpus plus petit pour un démarrage rapide
    print("Entraînement terminé !")
except Exception as e:
    print("Le chatbot est déjà entraîné ou une erreur s'est produite :", str(e))

# Fonction pour générer une réponse avec ChatterBot
def generate_chatterbot_response(query):
    try:
        response = chatbot.get_response(query)
        return str(response)
    except Exception as e:
        return f"Erreur lors de la génération de la réponse : {str(e)}"

# Layout
layout = html.Div([
    html.Div([
        html.H2("Real Chatbot", style={
            "fontSize": "2.8em",
            "fontWeight": "bold",
            "textAlign": "center",
            "marginTop": "60px",
            "color": "#ffffff",
            "textShadow": "0 0 8px #00eaff"
        }),

        # Zone de texte avec taille fixe
        html.Div(id="output-box1", style={
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
                id="input-box1",
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
            dbc.Button("Send", id="submit-button1", n_clicks=0, style={
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
            children=html.Div(id="loading-output1")
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
    Output("output-box1", "children"),
    Output("loading-output1", "children"),
    Input("submit-button1", "n_clicks"),
    State("input-box1", "value")
)
def update_output(n_clicks, value):
    if n_clicks > 0 and value:
        response = generate_chatterbot_response(value)
        return html.P(response, style={"color": "#ffffff"}), ""
    return "", ""