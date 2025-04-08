import dash
from dash import html, dcc
import dash_bootstrap_components as dbc
import requests
import pandas as pd
from dash.dependencies import Input, Output
import plotly.graph_objs as go

dash.register_page(__name__, path="/portfolio", name="Crypto Market")

# Couleur thème
theme_color = "#00eaff"

# Fonction pour récupérer les données crypto en temps réel via CoinGecko
def fetch_crypto_data():
    try:
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {
            "vs_currency": "usd",
            "order": "market_cap_desc",
            "per_page": 10,  # Top 10 cryptos
            "page": 1,
            "sparkline": True  # Activer la sparkline pour les 7 derniers jours
        }
        response = requests.get(url, params=params)
        response.raise_for_status()  # Lève une exception si la requête échoue
        data = response.json()
        
        if not data:  # Si la réponse est vide
            print("Aucune donnée reçue de l’API")
            return pd.DataFrame(columns=["Logo", "Name", "Symbol", "Price", "Market Cap", "24h Volume", "24h Change", "Sparkline"])
        
        # Log pour vérifier la réponse brute de l’API
        print("Réponse brute de l’API (première crypto) :", data[0])
        print("Sparkline_in_7d (première crypto) :", data[0].get("sparkline_in_7d", "Non présent"))

        # Formatter les données pour le tableau
        df = pd.DataFrame(data, columns=["image", "name", "symbol", "current_price", "market_cap", "total_volume", "price_change_percentage_24h", "sparkline_in_7d"])
        df["image"] = df["image"]  # URL de l’image
        df["current_price"] = df["current_price"].apply(lambda x: f"${x:,.2f}" if x else "N/A")
        df["market_cap"] = df["market_cap"].apply(lambda x: f"${x:,.0f}" if x else "N/A")
        df["total_volume"] = df["total_volume"].apply(lambda x: f"${x:,.0f}" if x else "N/A")
        df["price_change_percentage_24h"] = df["price_change_percentage_24h"].apply(lambda x: f"{x:.2f}%" if x else "N/A")
        # Extraire les données de la sparkline
        df["sparkline_in_7d"] = df["sparkline_in_7d"].apply(lambda x: x["price"] if isinstance(x, dict) and "price" in x else [])
        # Log pour vérifier les données de la sparkline après extraction
        print("Données de sparkline (première ligne) :", df["sparkline_in_7d"].iloc[0][:5] if len(df["sparkline_in_7d"].iloc[0]) > 0 else "Vide")
        df.columns = ["Logo", "Name", "Symbol", "Price", "Market Cap", "24h Volume", "24h Change", "Sparkline"]
        return df
    except Exception as e:
        print(f"Erreur lors de la récupération des données : {e}")
        return pd.DataFrame(columns=["Logo", "Name", "Symbol", "Price", "Market Cap", "24h Volume", "24h Change", "Sparkline"])

# Fonction pour récupérer l’historique des prix sur 7 jours (solution alternative)
def fetch_sparkline_data(coin_id):
    try:
        url = f"https://api.coingecko.com/api/v3/coins/{coin_id}/market_chart"
        params = {
            "vs_currency": "usd",
            "days": 7,
            "interval": "daily"
        }
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        prices = [price[1] for price in data["prices"]]  # Extraire les prix
        return prices
    except Exception as e:
        print(f"Erreur lors de la récupération de l’historique pour {coin_id} : {e}")
        return []

# Fonction pour générer un petit graphique sparkline
def create_sparkline(prices):
    if not prices or len(prices) < 2:
        print("Aucune donnée pour la sparkline")
        return html.Div("N/A", style={"color": "#ffffff", "textAlign": "center"})
    
    # Calculer la tendance (hausse ou baisse) sur 7 jours
    trend = (prices[-1] - prices[0]) / prices[0] if prices[0] != 0 else 0
    line_color = "#00cc00" if trend >= 0 else "#ff4d4d"  # Vert pour hausse, rouge pour baisse
    
    # Créer une courbe simple sans axes ni légende
    fig = go.Figure(
        data=[
            go.Scatter(
                x=list(range(len(prices))),
                y=prices,
                mode="lines",
                line={"color": line_color, "width": 1.5},
                hoverinfo="none"  # Désactiver les tooltips
            )
        ],
        layout={
            "height": 20,  # Réduire la hauteur
            "width": 60,   # Réduire la largeur
            "margin": {"l": 0, "r": 0, "t": 0, "b": 0},
            "xaxis": {"visible": False},
            "yaxis": {"visible": False},
            "paper_bgcolor": "rgba(0,0,0,0)",
            "plot_bgcolor": "rgba(0,0,0,0)"
        }
    )
    return dcc.Graph(figure=fig, config={"displayModeBar": False})

# Fonction pour générer le tableau HTML
def generate_table(data):
    if not data:
        return html.Table()
    
    # En-tête du tableau
    header = html.Tr([
        html.Th("Logo", style={"color": theme_color, "textAlign": "center", "padding": "10px", "borderBottom": f"2px solid {theme_color}", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"}),
        html.Th("Name", style={"color": theme_color, "textAlign": "left", "padding": "10px", "borderBottom": f"2px solid {theme_color}", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"}),
        html.Th("Symbol", style={"color": theme_color, "textAlign": "left", "padding": "10px", "borderBottom": f"2px solid {theme_color}", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"}),
        html.Th("Price", style={"color": theme_color, "textAlign": "left", "padding": "10px", "borderBottom": f"2px solid {theme_color}", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"}),
        html.Th("Market Cap", style={"color": theme_color, "textAlign": "left", "padding": "10px", "borderBottom": f"2px solid {theme_color}", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"}),
        html.Th("24h Volume", style={"color": theme_color, "textAlign": "left", "padding": "10px", "borderBottom": f"2px solid {theme_color}", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"}),
        html.Th("24h Change", style={"color": theme_color, "textAlign": "left", "padding": "10px", "borderBottom": f"2px solid {theme_color}", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"}),
        html.Th("Trend (7d)", style={"color": theme_color, "textAlign": "center", "padding": "10px", "borderBottom": f"2px solid {theme_color}", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"})
    ])
    
    # Lignes du tableau
    rows = []
    for row in data:
        change_color = "#ff4d4d" if "-" in row["24h Change"] else "#00cc00"
        rows.append(html.Tr([
            html.Td(html.Img(src=row["Logo"], style={"width": "30px", "height": "30px"}), style={"textAlign": "center", "padding": "10px"}),
            html.Td(row["Name"], style={"color": "#ffffff", "textAlign": "left", "padding": "10px", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"}),
            html.Td(row["Symbol"], style={"color": "#ffffff", "textAlign": "left", "padding": "10px", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"}),
            html.Td(row["Price"], style={"color": "#ffffff", "textAlign": "left", "padding": "10px", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"}),
            html.Td(row["Market Cap"], style={"color": "#ffffff", "textAlign": "left", "padding": "10px", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"}),
            html.Td(row["24h Volume"], style={"color": "#ffffff", "textAlign": "left", "padding": "10px", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"}),
            html.Td(row["24h Change"], style={"color": change_color, "textAlign": "left", "padding": "10px", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"}),
            html.Td(create_sparkline(row["Sparkline"]), style={"textAlign": "center", "padding": "10px", "width": "80px"})
        ]))
    
    return html.Table([header] + rows, style={
        "overflowX": "auto",
        "maxWidth": "90%",
        "margin": "0 auto",
        "backgroundColor": "transparent",
        "border": "none",
        "width": "100%"
    })

# Mise en page
layout = html.Div([
    # Titre
    html.H1("Crypto Market Live", style={
        "fontSize": "4rem",
        "fontWeight": "700",
        "color": "#ffffff",
        "textAlign": "center",
        "textShadow": f"0 0 20px {theme_color}, 0 0 40px {theme_color}",
        "marginTop": "80px",
        "marginBottom": "40px",
        "animation": "glowIn 2s ease forwards"
    }),
    
    # Sous-titre
    html.P("Real-time top 10 cryptocurrency market data", style={
        "fontSize": "1.5rem",
        "color": "#cccccc",
        "textAlign": "center",
        "marginBottom": "30px",
        "animation": "fadeIn 1.5s 0.5s forwards"
    }),
    
    # Message d’erreur ou de chargement
    html.Div(id="error-message", style={
        "color": "#ff4d4d",
        "textAlign": "center",
        "fontSize": "1.2rem",
        "marginBottom": "20px"
    }),
    
    # Tableau des données
    html.Div(id="crypto-table-container"),
    
    # Intervalle pour mise à jour toutes les 60 secondes
    dcc.Interval(id="interval-component", interval=60*1000, n_intervals=0)
])

# Callback pour mettre à jour le tableau et gérer les erreurs
@dash.callback(
    [Output("crypto-table-container", "children"),
     Output("error-message", "children")],
    Input("interval-component", "n_intervals")
)
def update_table(n_intervals):
    df = fetch_crypto_data()
    if df.empty:
        return [], "Erreur : Impossible de récupérer les données. Vérifie ta connexion ou réessaie plus tard."
    data = df.to_dict("records")
    
    # Si les sparklines sont vides, utiliser l’endpoint alternatif pour chaque crypto
    for i, row in enumerate(data):
        if not row["Sparkline"]:
            coin_id = row["Name"].lower().replace(" ", "-")  # Ex. "Bitcoin" -> "bitcoin"
            print(f"Récupération des données de sparkline pour {coin_id} via l’endpoint alternatif")
            prices = fetch_sparkline_data(coin_id)
            data[i]["Sparkline"] = prices
    
    return generate_table(data), ""