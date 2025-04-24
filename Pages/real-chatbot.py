import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import cohere

dash.register_page(__name__, path="/real-chatbot", name="Real Chatbot")

theme_color = "#00eaff"

# Initialiser le client Cohere avec votre clé API
COHERE_API_KEY = "4CqRZV9kpf0w3jZfR9e2OXJarFfW0oP0gGwlvICD"  # Remplacez par votre clé API
cohere_client = cohere.Client(COHERE_API_KEY)

# Fonction de réponse avec Cohere
def generate_cohere_response(query, chat_history=None):
    try:
        # Construire l'historique pour le contexte (facultatif, pour une conversation plus fluide)
        prompt = ""
        if chat_history:
            for entry in chat_history[-4:]:  # Limiter à 4 derniers messages pour éviter un prompt trop long
                if entry["sender"] == "user":
                    prompt += f"User: {entry['message']}\n"
                else:
                    prompt += f"Bot: {entry['message']}\n"
        prompt += f"User: {query}\nBot: "

        # Appeler l'API Cohere pour générer une réponse
        response = cohere_client.generate(
            model="command",  # Modèle recommandé pour la conversation
            prompt=prompt,
            max_tokens=150,   # Limite la longueur de la réponse
            temperature=0.7,  # Contrôle la créativité (0 = déterministe, 1 = créatif)
            stop_sequences=["\n"]  # Arrête la génération à la fin de la réponse
        )

        return response.generations[0].text.strip()
    except Exception as e:
        return f"Erreur : {str(e)}"


# Bubble style generator
def message_bubble(message, sender="user"):
    align = "flex-end" if sender == "user" else "flex-start"
    bg_color = theme_color if sender == "user" else "rgba(255, 255, 255, 0.1)"
    color = "#0a0a0a" if sender == "user" else "#ffffff"
    border_radius = "20px 20px 0 20px" if sender == "user" else "20px 20px 20px 0"

    return html.Div(
        message,
        style={
            "maxWidth": "70%",
            "alignSelf": align,
            "backgroundColor": bg_color,
            "color": color,
            "padding": "12px 18px",
            "margin": "8px 0",
            "borderRadius": border_radius,
            "boxShadow": f"0 0 10px {theme_color if sender == 'user' else '#ffffff44'}",
            "animation": "fadeIn 0.4s ease-in-out",
        }
    )

# Layout
layout = html.Div([
    dcc.Store(id="chat-store"),

    html.Div([
        html.H1("💬 CryptoBot", style={
            "textAlign": "center",
            "color": "#00eaff",
            "marginBottom": "10px",
            "textShadow": "0 0 15px #00eaff88"
        }),

        html.Div(id="chat-history", style={
            "display": "flex",
            "flexDirection": "column",
            "gap": "10px",
            "padding": "20px",
            "backgroundColor": "#0d0d1a",
            "borderRadius": "20px",
            "boxShadow": "0 0 25px #00eaff55",
            "overflowY": "auto",
            "flexGrow": "1",
        }),

        html.Div([
            dcc.Input(id="input-box1", type="text", placeholder="Typez votre message...",
                      style={
                          "width": "100%",
                          "padding": "15px",
                          "borderRadius": "12px",
                          "border": "none",
                          "outline": "none",
                          "fontSize": "16px",
                          "marginRight": "10px",
                      }),
            html.Button("Envoyer", id="submit-button1", n_clicks=0,
                        style={
                            "padding": "10px 20px",
                            "borderRadius": "12px",
                            "border": "none",
                            "backgroundColor": "#00eaff",
                            "color": "#0d0d1a",
                            "fontWeight": "bold"
                        })
        ], style={"display": "flex", "marginTop": "20px"})
    
    ], style={
        "display": "flex",
        "flexDirection": "column",
        "height": "100%",
        "maxHeight": "90vh",
        "width": "100%",
        "maxWidth": "800px",
        "margin": "auto",
        "background": "radial-gradient(circle at top left, #0f172a, #0d0d1a)",
        "padding": "30px",
        "borderRadius": "25px",
        "boxShadow": "0 0 30px #00eaff44",
    }),
], style={
    "height": "100vh",
    "display": "flex",
    "alignItems": "center",
    "justifyContent": "center",
    "overflow": "hidden"  # Empêche le défilement sur la page
})

# Callback pour gérer la conversation
@dash.callback(
    Output("chat-store", "data"),
    Output("chat-history", "children"),
    Input("submit-button1", "n_clicks"),
    State("input-box1", "value"),
    State("chat-store", "data"),
    prevent_initial_call=True
)
def update_chat(n_clicks, user_input, chat_history):
    if not user_input:
        return chat_history, dash.no_update

    if chat_history is None:
        chat_history = []

    # Générer la réponse avec Cohere
    bot_response = generate_cohere_response(user_input, chat_history)

    # Ajouter le message de l'utilisateur et la réponse du bot à l'historique
    chat_history.append({"sender": "user", "message": user_input})
    chat_history.append({"sender": "bot", "message": bot_response})

    # Créer les bulles de message pour l'affichage
    bubbles = []
    for entry in chat_history:
        bubbles.append(message_bubble(entry["message"], entry["sender"]))

    return chat_history, bubbles