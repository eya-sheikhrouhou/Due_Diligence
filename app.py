import dash
from dash import html, dcc, Input, Output, State, no_update
import dash_bootstrap_components as dbc
from flask import session
import bcrypt
from pymongo import MongoClient
import datetime

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG], use_pages=True)
app.title = "Crypto Due Diligence"

# Connexion à MongoDB
try:
    client = MongoClient("mongodb://localhost:27017/")
    db = client["due_diligence_db"]
    users_collection = db["users"]
    print("Connexion à MongoDB réussie.")
except Exception as e:
    print(f"Erreur de connexion à MongoDB : {str(e)}")

# Configurer Flask pour les sessions
app.server.secret_key = "super_secret_key_123"  # Change en prod !

# Index HTML
app.index_string = '''
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Crypto Due Diligence</title>
        <link rel="icon" href="/assets/favicon.ico" type="image/x-icon">
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap" rel="stylesheet">
        {%metas%}
        {%css%}
        <style>
            body {
                background: #0a0a0a;
                color: #ffffff;
                font-family: 'Inter', sans-serif;
                margin: 0;
                overflow-x: hidden;
            }
            .background {
                position: fixed;
                width: 100%;
                height: 100vh;
                background: linear-gradient(135deg, #0a0a0a, #003366, #1a0033);
                background-size: 400% 400%;
                animation: nebulaFlow 20s ease infinite;
                z-index: -1;
                opacity: 0.8;
            }
            .stars {
                position: fixed;
                width: 100%;
                height: 100vh;
                background: radial-gradient(circle, rgba(255,255,255,0.1) 1px, transparent 1px);
                background-size: 30px 30px;
                animation: starFlow 50s linear infinite;
                z-index: -1;
            }
            .navbar {
                background: rgba(0, 0, 0, 0) !important;
                backdrop-filter: blur(15px);
                padding: 15px 20px;
                position: fixed;
                top: 0;
                width: 100%;
                z-index: 1000;
                border-bottom: none !important;
                box-shadow: none !important;
            }
            .nav-link {
                font-size: 1.2rem;
                color: #ffffff !important;
                transition: color 0.3s;
            }
            .nav-link:hover {
                color: #00eaff !important;
            }
            .login-button {
                background: linear-gradient(45deg, #00eaff, #00b4d8);
                color: #0a0a0a;
                padding: 8px 20px;
                font-size: 1.1rem;
                font-weight: bold;
                border-radius: 20px;
                border: none;
                box-shadow: 0 0 10px #00eaff;
                transition: transform 0.3s, box-shadow 0.3s;
            }
            .login-button:hover {
                transform: scale(1.05);
                box-shadow: 0 0 20px #00eaff;
                color: #0a0a0a !important;
            }
            .content {
                padding-top: 80px;
            }
            .main-title {
                font-size: 6rem;
                font-weight: 800;
                color: #ffffff;
                text-align: center;
                text-shadow: 0 0 20px #00eaff, 0 0 40px #00eaff;
                opacity: 0;
                animation: glowIn 2s ease forwards;
            }
            .subtext {
                font-size: 1.8rem;
                color: #cccccc;
                text-align: center;
                margin-top: 20px;
                opacity: 0;
                animation: fadeIn 1.5s 0.5s forwards;
            }
            .button-start {
                background: #00eaff;
                color: #0a0a0a;
                padding: 15px 40px;
                font-size: 1.5em;
                font-weight: bold;
                margin-top: 40px;
                border: none;
                border-radius: 30px;
                box-shadow: 0 0 15px #00eaff;
                transition: transform 0.3s;
                animation: pulse 2s infinite;
            }
            .button-start:hover {
                transform: scale(1.05);
            }
            @keyframes nebulaFlow {
                0% { background-position: 0% 0%; }
                50% { background-position: 100% 100%; }
                100% { background-position: 0% 0%; }
            }
            @keyframes starFlow {
                0% { transform: translateX(0); }
                100% { transform: translateX(-1000px); }
            }
            @keyframes glowIn {
                0% { opacity: 0; transform: scale(0.9); text-shadow: 0 0 10px #00eaff; }
                100% { opacity: 1; transform: scale(1); text-shadow: 0 0 20px #00eaff, 0 0 40px #00eaff; }
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(-10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            @keyframes pulse {
                0% { box-shadow: 0 0 5px #00eaff; }
                50% { box-shadow: 0 0 15px #00eaff; }
                100% { box-shadow: 0 0 5px #00eaff; }
            }
        </style>
    </head>
    <body>
        <div class="background"></div>
        <div class="stars"></div>
        {%app_entry%}
        <footer>
            {%config%}
            {%scripts%}
            {%renderer%}
        </footer>
    </body>
</html>
'''

# Vérification de connexion
def is_user_logged_in():
    return "user_id" in session

# Navbar dynamique
def create_navbar():
    if is_user_logged_in():
        login_logout_item = dbc.NavItem(dbc.Button("🔓 Logout", className="login-button", id="logout-button"))
    else:
        login_logout_item = dbc.NavItem(dbc.Button("🔒 Login", className="login-button", href="/login"))
    
    return dbc.Navbar(
        dbc.Container([
            dbc.Row([
                dbc.Col(html.Img(src="/assets/Logo.png", height="100px"), width="auto"),
            ], align="center", className="g-0"),
            dbc.Nav([
                dbc.NavItem(dbc.NavLink("Home", href="/", className="nav-link")),
                dbc.NavItem(dbc.NavLink("Real Chatbot", href="/real-chatbot", className="nav-link")),
                dbc.NavItem(dbc.NavLink("Banque Réponse", href="/banque_reponse", className="nav-link")),
                dbc.NavItem(dbc.NavLink("Banque Question", href="/banque_question", className="nav-link")),
                dbc.NavItem(dbc.NavLink("Crypto Market", href="/portfolio", className="nav-link")),
                dbc.NavItem(dbc.NavLink("Resources", href="/resources", className="nav-link")),
                login_logout_item,
            ], navbar=True, className="ms-auto")
        ], fluid=True),
        className="navbar",
        dark=False,
        color="transparent"
    )

# Mise en page principale
app.layout = html.Div([
    dcc.Location(id="url", refresh=False),
    html.Div(id="navbar-container"),
    html.Div(dash.page_container, className="content"),
    dcc.Store(id="login-status", storage_type="session")
])

# Page d'inscription
signup_layout = html.Div([
    html.H2("Inscription", style={
        "fontSize": "2.8em", "fontWeight": "bold", "textAlign": "center",
        "marginTop": "60px", "color": "#ffffff", "textShadow": "0 0 8px #00eaff"
    }),
    html.Div([
        dcc.Input(id="signup-email", type="email", placeholder="Email", style={
            "width": "300px", "padding": "10px", "margin": "10px",
            "borderRadius": "5px", "border": "1px solid #00eaff", "color": "#ffffff",
            "background": "transparent"
        }),
        dcc.Input(id="signup-password", type="password", placeholder="Mot de passe", style={
            "width": "300px", "padding": "10px", "margin": "10px",
            "borderRadius": "5px", "border": "1px solid #00eaff", "color": "#ffffff",
            "background": "transparent"
        }),
        dbc.Button("S'inscrire", id="signup-button", style={
            "backgroundColor": "#00eaff", "border": "none", "color": "#0a0a0a",
            "padding": "10px 25px", "fontWeight": "bold", "borderRadius": "8px",
            "boxShadow": "0 0 10px #00eaff", "margin": "20px"
        }),
        html.Div(id="signup-output", style={"color": "#ffffff", "textAlign": "center"}),
        html.A("Déjà un compte ? Connectez-vous", href="/login", style={"color": "#00eaff"})
    ], style={"display": "flex", "flexDirection": "column", "alignItems": "center"})
], style={"minHeight": "100vh", "padding": "30px"})

# Page de connexion
login_layout = html.Div([
    html.H2("Connexion", style={
        "fontSize": "2.8em", "fontWeight": "bold", "textAlign": "center",
        "marginTop": "60px", "color": "#ffffff", "textShadow": "0 0 8px #00eaff"
    }),
    html.Div([
        dcc.Input(id="login-email", type="email", placeholder="Email", style={
            "width": "300px", "padding": "10px", "margin": "10px",
            "borderRadius": "5px", "border": "1px solid #00eaff", "color": "#ffffff",
            "background": "transparent"
        }),
        dcc.Input(id="login-password", type="password", placeholder="Mot de passe", style={
            "width": "300px", "padding": "10px", "margin": "10px",
            "borderRadius": "5px", "border": "1px solid #00eaff", "color": "#ffffff",
            "background": "transparent"
        }),
        dbc.Button("Se connecter", id="login-button", style={
            "backgroundColor": "#00eaff", "border": "none", "color": "#0a0a0a",
            "padding": "10px 25px", "fontWeight": "bold", "borderRadius": "8px",
            "boxShadow": "0 0 10px #00eaff", "margin": "20px"
        }),
        html.Div(id="login-output", style={"color": "#ffffff", "textAlign": "center"}),
        html.A("Pas de compte ? Inscrivez-vous", href="/signup", style={"color": "#00eaff"})
    ], style={"display": "flex", "flexDirection": "column", "alignItems": "center"})
], style={"minHeight": "100vh", "padding": "30px"})

# Enregistrer les pages
dash.register_page("login", path="/login", layout=login_layout, name="Login")
dash.register_page("signup", path="/signup", layout=signup_layout, name="Signup")

# Callbacks
@app.callback(
    Output("navbar-container", "children"),
    Input("url", "pathname"),
    Input("login-status", "data")
)
def update_navbar(pathname, login_status):
    return create_navbar()

@app.callback(
    Output("signup-output", "children"),
    Input("signup-button", "n_clicks"),
    State("signup-email", "value"),
    State("signup-password", "value"),
    prevent_initial_call=True
)
def signup(n_clicks, email, password):
    if not email or not password:
        return "Veuillez remplir tous les champs."
    
    if users_collection.find_one({"email": email}):
        return "Cet email est déjà utilisé."
    
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    user_doc = {
        "email": email,
        "password": hashed_password,
        "created_at": datetime.datetime.utcnow()
    }
    
    try:
        result = users_collection.insert_one(user_doc)
        session["user_id"] = str(result.inserted_id)
        return html.Div([dcc.Location(href="/", id="redirect-home")])
    except Exception as e:
        return f"Erreur : {str(e)}"

@app.callback(
    Output("login-output", "children"),
    Input("login-button", "n_clicks"),
    State("login-email", "value"),
    State("login-password", "value"),
    prevent_initial_call=True
)
def login(n_clicks, email, password):
    if not email or not password:
        return "Veuillez remplir tous les champs."
    
    user = users_collection.find_one({"email": email})
    if not user:
        return "Email ou mot de passe incorrect."
    
    if bcrypt.checkpw(password.encode("utf-8"), user["password"]):
        session["user_id"] = str(user["_id"])
        return html.Div([dcc.Location(href="/", id="redirect-home")])
    else:
        return "Email ou mot de passe incorrect."

@app.callback(
    Output("login-status", "data"),
    Input("logout-button", "n_clicks"),
    prevent_initial_call=True
)
def logout(n_clicks):
    if n_clicks:
        session.pop("user_id", None)
        return {"redirect": "/login"}
    return no_update

@app.callback(
    Output("url", "pathname"),
    Input("url", "pathname"),
    prevent_initial_call=True
)
def protect_pages(pathname):
    protected_pages = ["/real-chatbot", "/banque_reponse", "/banque_question", "/portfolio", "/resources"]
    if pathname in protected_pages and not is_user_logged_in():
        return "/login"
    return no_update

if __name__ == "__main__":
    app.run_server(debug=True, port=8050)