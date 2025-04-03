import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

# Initialisation de l'application
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.DARKLY], use_pages=True)
app.title = "Crypto Due Diligence"

# Nouveau HTML avec fond animé et effets futuristes
app.index_string = '''
<!DOCTYPE html>
<html lang="en">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>Crypto Due Diligence</title>
        <link rel="icon" href="/assets/favicon.ico" type="image/x-icon">
        <link href="https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700&display=swap" rel="stylesheet">
        {%metas%}
        {%css%}
        <style>
            body {
                background: #050A30;
                color: #ffffff;
                font-family: 'Orbitron', sans-serif;
                margin: 0;
                overflow-x: hidden;
            }
            
            /* Fond animé avec effet néon */
            .background {
                position: fixed;
                width: 100%;
                height: 100vh;
                background: radial-gradient(circle, #021B79, #051937, #000000);
                animation: neonGlow 10s infinite alternate;
                z-index: -2;
            }

            @keyframes neonGlow {
                0% { filter: brightness(1); }
                100% { filter: brightness(1.3); }
            }

            /* Effet d'étoiles mouvantes */
            .stars {
                position: fixed;
                width: 100%;
                height: 100vh;
                background: url('/assets/stars.png') repeat;
                animation: moveStars 50s linear infinite;
                z-index: -1;
            }

            @keyframes moveStars {
                from { transform: translateY(0); }
                to { transform: translateY(-1000px); }
            }

            /* Navbar futuriste */
            .navbar {
                backdrop-filter: blur(15px);
                background: rgba(10, 10, 10, 0.7);
                padding: 15px 20px;
                position: fixed;
                top: 0;
                width: 100%;
                z-index: 1000;
                box-shadow: 0 0 20px #00eaff;
            }

            .nav-link {
                font-size: 1.2rem;
                color: #ffffff !important;
                transition: color 0.3s, text-shadow 0.3s;
            }

            .nav-link:hover {
                color: #00eaff !important;
                text-shadow: 0 0 10px #00eaff;
            }

            /* Bouton login futuriste */
            .login-button {
                background: linear-gradient(45deg, #00eaff, #0033ff);
                color: #ffffff;
                padding: 10px 20px;
                font-size: 1.1rem;
                font-weight: bold;
                border-radius: 30px;
                border: none;
                box-shadow: 0 0 15px #00eaff;
                transition: transform 0.3s, box-shadow 0.3s;
            }

            .login-button:hover {
                transform: scale(1.1);
                box-shadow: 0 0 25px #00eaff;
            }

            .content {
                padding-top: 100px;
            }

            /* Titre principal holographique */
            .main-title {
                font-size: 5rem;
                font-weight: 800;
                color: #00eaff;
                text-align: center;
                text-shadow: 0 0 20px #00eaff, 0 0 40px #00b4ff;
                opacity: 0;
                animation: glowIn 2s ease forwards;
            }

            @keyframes glowIn {
                0% { opacity: 0; transform: scale(0.9); text-shadow: 0 0 10px #00eaff; }
                100% { opacity: 1; transform: scale(1); text-shadow: 0 0 30px #00eaff, 0 0 50px #00b4ff; }
            }

            /* Bouton principal */
            .button-start {
                background: linear-gradient(45deg, #00eaff, #0033ff);
                color: #ffffff;
                padding: 15px 40px;
                font-size: 1.5em;
                font-weight: bold;
                border: none;
                border-radius: 30px;
                box-shadow: 0 0 20px #00eaff;
                transition: transform 0.3s, box-shadow 0.3s;
                animation: pulse 2s infinite;
            }

            .button-start:hover {
                transform: scale(1.1);
                box-shadow: 0 0 30px #00eaff;
            }

            @keyframes pulse {
                0% { box-shadow: 0 0 10px #00eaff; }
                50% { box-shadow: 0 0 25px #00eaff; }
                100% { box-shadow: 0 0 10px #00eaff; }
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

# Navbar futuriste
navbar = dbc.Navbar(
    dbc.Container([
        dbc.Row([
            dbc.Col(html.Img(src="/assets/Logo.png", height="50px"), width="auto"),
            dbc.Col(dbc.NavbarBrand("CHAINVESTOR HUB", href="/", className="navbar-brand"), width="auto"),
        ], align="center", className="g-0"),
        dbc.Nav([
            dbc.NavItem(dbc.NavLink("🏠 Home", href="/", className="nav-link")),
            dbc.NavItem(dbc.NavLink("🤖 Chatbot", href="/chatbot", className="nav-link")),
            dbc.NavItem(dbc.NavLink("📈 Crypto Market", href="/portfolio", className="nav-link")),
            dbc.NavItem(dbc.NavLink("📚 Resources", href="/resources", className="nav-link")),
            dbc.NavItem(dbc.Button("🔒 Login", className="login-button", href="#")),
        ], navbar=True, className="ms-auto")
    ], fluid=True),
    className="navbar"
)

# Layout principal
app.layout = html.Div([
    navbar,
    html.Div(dash.page_container, className="content")
])

if __name__ == "__main__":
    app.run_server(debug=True, port=8050)
