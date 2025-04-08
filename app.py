import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

app = dash.Dash(__name__, external_stylesheets=[dbc.themes.CYBORG], use_pages=True)
app.title = "Crypto Due Diligence"

# Index HTML avec fond spatial animé et toutes les animations
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
    background: rgba(0, 0, 0, 0) !important; /* Transparence totale */
    backdrop-filter: blur(15px);
    padding: 15px 20px;
    position: fixed;
    top: 0;
    width: 100%;
    z-index: 1000;
    border-bottom: none !important; /* Supprime toute bordure éventuelle */
    box-shadow: none !important; /* Supprime toute ombre éventuelle */
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

# Navbar modifiée en anglais
navbar = dbc.Navbar(
    dbc.Container([
        dbc.Row([
            dbc.Col(html.Img(src="/assets/Logo.png", height="100px"), width="auto"),

        ], align="center", className="g-0"),
        dbc.Nav([
            dbc.NavItem(dbc.NavLink("Home", href="/", className="nav-link")),
            dbc.NavItem(dbc.NavLink("real-chatbot", href="/real-chatbot", className="nav-link")),
            dbc.NavItem(dbc.NavLink("banque_reponse", href="/banque_reponse", className="nav-link")),
            dbc.NavItem(dbc.NavLink("banque_question", href="/banque_question", className="nav-link")),
            dbc.NavItem(dbc.NavLink("Crypto Market", href="/portfolio", className="nav-link")),
            dbc.NavItem(dbc.NavLink("Resources", href="/resources", className="nav-link")),
            dbc.NavItem(dbc.Button("🔒 Login", className="login-button", href="#")),
        ], navbar=True, className="ms-auto")
    ], fluid=True),
    className="navbar",
    dark=False,  # Désactive le mode sombre de Bootstrap
    color="transparent"  # Définit la couleur sur transparent
)


# Mise en page principale
app.layout = html.Div([
    navbar,
    html.Div(dash.page_container, className="content")
])

if __name__ == "__main__":
    app.run_server(debug=True, port=8050)