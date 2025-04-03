import dash
from dash import html, dcc
import dash_bootstrap_components as dbc

dash.register_page(__name__, path="/")

layout = html.Div([
    html.Div([
        html.H1("Crypto Due Diligence", className="main-title"),
        html.P("Next-generation crypto analysis.", className="subtext"),
        dbc.Button("Explore", href="/chatbot", className="button-start")
    ], style={
        "height": "100vh",
        "display": "flex",
        "flexDirection": "column",
        "alignItems": "center",
        "justifyContent": "center",
        "textAlign": "center"
    })
])