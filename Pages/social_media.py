import dash
from dash import html, dcc, dash_table, callback, clientside_callback
import dash_bootstrap_components as dbc
from dash.dependencies import Input, Output, State
import pandas as pd
import time
import json
import os
import requests
from newsapi import NewsApiClient
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from pages.portfolio import fetch_crypto_data

dash.register_page(__name__, path="/social_media", name="Crypto Social Media")

sentiment_analyzer = SentimentIntensityAnalyzer()

# Color theme
theme_color = "#00eaff"
obsidian_black = "#0a0f1a"
sapphire_blue = "#1e3a8a"
platinum_silver = "#d1d5db"
neon_green = "#00cc00"
crimson_red = "#ff4d4d"
neutral_grey = "#cccccc"

# Cache file for social media data
CACHE_FILE = "social_media_cache.json"

# List of top 10 cryptocurrencies (aligned with fetch_crypto_data)
TOP_10_COINS = [
    "bitcoin", "ethereum", "tether", "xrp", "bnb",
    "solana", "usd-coin", "dogecoin", "cardano", "tron"
]

# NewsAPI configuration
NEWSAPI_KEY = "3ac547f4352140d2855385cceb9f96c2"  # Replace with your full API key
newsapi = NewsApiClient(api_key=NEWSAPI_KEY)

def fetch_new_social_media_posts(coins=TOP_10_COINS):
    posts = []

    # Fetch crypto data to get logos and price changes
    df = fetch_crypto_data()
    coin_map = {row["Name"].lower(): row for row in df.to_dict("records")}

    # Fetch articles via NewsAPI
    try:
        for coin in coins:
            print(f"Fetching articles for {coin}")
            articles = newsapi.get_everything(
                q=coin,
                language="en",
                sort_by="publishedAt",
                page_size=1
            )
            print(f"NewsAPI response for {coin}: {articles}")
            if articles["status"] == "ok" and articles["articles"]:
                for article in articles["articles"]:
                    print(f"Article found for {coin}: {article['title']}")
                    posts.append({
                        "id": article.get("url", str(int(time.time()))),
                        "text": article.get("title", "") + " - " + (article.get("description", "") or "")[:280],
                        "created_at": article.get("publishedAt", time.strftime("%Y-%m-%d %H:%M:%S")),
                        "user": article.get("source", {}).get("name", "Unknown"),
                        "platform": "News",
                        "coin": coin,
                        "logo": coin_map.get(coin.lower(), {}).get("Logo", "")  # Add logo URL
                    })
            else:
                print(f"No articles found for {coin}: {articles}")
    except Exception as e:
        print(f"Error fetching NewsAPI data: {e}")
        # Fallback data
        posts = [
            {
                "id": str(int(time.time())),
                "coin": "bitcoin",
                "text": "New article about #bitcoin! Market is volatile! ⚡",
                "user": "CryptoNews",
                "platform": "News",
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "logo": coin_map.get("bitcoin", {}).get("Logo", "")
            },
            {
                "id": str(int(time.time()) + 1),
                "coin": "ethereum",
                "text": "#ethereum adoption growing fast! 🚀",
                "user": "CryptoNews",
                "platform": "News",
                "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "logo": coin_map.get("ethereum", {}).get("Logo", "")
            }
        ]

    # Add sentiment and price change
    for post in posts:
        coin = post["coin"].lower()
        sentiment_scores = sentiment_analyzer.polarity_scores(post["text"])
        post["sentiment"] = "positive" if sentiment_scores["compound"] > 0.05 else "negative" if sentiment_scores["compound"] < -0.05 else "neutral"
        post["sentiment_score"] = sentiment_scores["compound"]
        if coin in coin_map and "24h Change" in coin_map[coin]:
            price_change = coin_map[coin]["24h Change"]
            try:
                if isinstance(price_change, str):
                    price_change = float(price_change.replace("%", ""))
                post["price_change_24h"] = float(price_change)
            except (ValueError, TypeError) as e:
                print(f"Error converting price_change for {coin}: {price_change}, Error: {e}")
                post["price_change_24h"] = 0.0
        else:
            print(f"Missing data for {coin} in coin_map or '24h Change' absent")
            post["price_change_24h"] = 0.0

    return posts

def save_cache(data):
    cache = {"timestamp": time.time(), "data": data}
    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)

def load_cache():
    if os.path.exists(CACHE_FILE):
        with open(CACHE_FILE, "r") as f:
            cache = json.load(f)
            if "timestamp" in cache and (time.time() - cache["timestamp"]) < 600:
                df = fetch_crypto_data()
                coin_map = {row["Name"].lower(): row for row in df.to_dict("records")}
                updated_data = []
                for post in cache["data"]:
                    if "logo" not in post or not post["logo"]:
                        coin = post["coin"].lower()
                        post["logo"] = coin_map.get(coin, {}).get("Logo", "")
                    updated_data.append(post)
                return updated_data
    return []

def generate_social_media_table(posts):
    if not posts:
        return html.Table()
    
    header = html.Tr([
        html.Th("Logo", style={"color": theme_color, "textAlign": "center", "padding": "10px", "borderBottom": f"2px solid {theme_color}", "textShadow": f"0 0 5px rgba(0, 234, 255, 0.5)"}),
        html.Th("Coin", style={"color": theme_color, "textAlign": "left", "padding": "10px", "borderBottom": f"2px solid {theme_color}", "textShadow": f"0 0 5px rgba(0, 234, 255, 0.5)"}),
        html.Th("Post", style={"color": theme_color, "textAlign": "left", "padding": "10px", "borderBottom": f"2px solid {theme_color}", "textShadow": f"0 0 5px rgba(0, 234, 255, 0.5)"}),
        html.Th("User", style={"color": theme_color, "textAlign": "left", "padding": "10px", "borderBottom": f"2px solid {theme_color}", "textShadow": f"0 0 5px rgba(0, 234, 255, 0.5)"}),
        html.Th("Platform", style={"color": theme_color, "textAlign": "left", "padding": "10px", "borderBottom": f"2px solid {theme_color}", "textShadow": f"0 0 5px rgba(0, 234, 255, 0.5)"}),
        html.Th("Date", style={"color": theme_color, "textAlign": "left", "padding": "10px", "borderBottom": f"2px solid {theme_color}", "textShadow": f"0 0 5px rgba(0, 234, 255, 0.5)"}),
        html.Th("Sentiment", style={"color": theme_color, "textAlign": "left", "padding": "10px", "borderBottom": f"2px solid {theme_color}", "textShadow": f"0 0 5px rgba(0, 234, 255, 0.5)"}),
        html.Th("24h Price Change", style={"color": theme_color, "textAlign": "left", "padding": "10px", "borderBottom": f"2px solid {theme_color}", "textShadow": f"0 0 5px rgba(0, 234, 255, 0.5)"})
    ])
    
    rows = []
    for post in posts:
        sentiment_color = neon_green if post["sentiment"] == "positive" else crimson_red if post["sentiment"] == "negative" else neutral_grey
        change_color = crimson_red if post["price_change_24h"] < 0 else neon_green
        rows.append(html.Tr([
            html.Td(
                html.Img(src=post.get("logo", ""), style={"width": "30px", "height": "30px"}) if post.get("logo") else "N/A",
                style={"textAlign": "center", "padding": "10px"}
            ),
            html.Td(post["coin"].capitalize(), style={"color": platinum_silver, "textAlign": "left", "padding": "10px", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"}),
            html.Td(post["text"][:100] + "..." if len(post["text"]) > 100 else post["text"], style={"color": platinum_silver, "textAlign": "left", "padding": "10px", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"}),
            html.Td(post["user"], style={"color": platinum_silver, "textAlign": "left", "padding": "10px", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"}),
            html.Td(post["platform"], style={"color": platinum_silver, "textAlign": "left", "padding": "10px", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"}),
            html.Td(post["created_at"], style={"color": platinum_silver, "textAlign": "left", "padding": "10px", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"}),
            html.Td(post["sentiment"], style={"color": sentiment_color, "textAlign": "left", "padding": "10px", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"}),
            html.Td(f"{post['price_change_24h']:.2f}%", style={"color": change_color, "textAlign": "left", "padding": "10px", "textShadow": "0 0 5px rgba(0, 234, 255, 0.5)"})
        ]))
    
    return html.Table([header] + rows, style={
        "overflowX": "auto",
        "maxWidth": "90%",
        "margin": "0 auto",
        "backgroundColor": "transparent",
        "border": "none",
        "width": "100%"
    })

def predict_investment_model(posts):
    if not posts:
        return html.Div("No data available to predict investment decision.", style={
            "color": platinum_silver,
            "textAlign": "center",
            "fontSize": "1.2rem",
            "margin": "20px 0"
        })

    df = pd.DataFrame(posts)
    predictions = []

    for coin in df["coin"].unique():
        coin_posts = df[df["coin"] == coin]
        recent_posts = coin_posts.tail(5)
        avg_sentiment = recent_posts["sentiment_score"].mean() if not recent_posts.empty else 0
        price_change = coin_posts["price_change_24h"].iloc[-1] if not coin_posts.empty else 0

        sentiment_weight = float(avg_sentiment) * 50
        price_weight = float(price_change) * 2
        risk_score = sentiment_weight + price_weight

        if risk_score > 20:
            recommendation = "Investir"
            color = neon_green
            justification = f"Sentiment positif ({avg_sentiment:.2f}) et variation de prix ({price_change:.2f}%) indiquent un potentiel de croissance."
        elif risk_score < -20:
            recommendation = "Ne pas investir"
            color = crimson_red
            justification = f"Sentiment négatif ({avg_sentiment:.2f}) et variation de prix ({price_change:.2f}%) suggèrent un risque élevé."
        else:
            recommendation = "Attendre"
            color = neutral_grey
            justification = f"Sentiment neutre ({avg_sentiment:.2f}) et variation de prix ({price_change:.2f}%) indiquent une situation incertaine."

        predictions.append({
            "coin": coin.capitalize(),
            "recommendation": recommendation,
            "color": color,
            "justification": justification
        })

    # Create a grid layout for predictions
    prediction_cards = []
    for idx, prediction in enumerate(predictions):
        card_id = f"prediction-card-{idx}"
        justification_id = f"justification-{idx}"
        prediction_cards.append(
            html.Div(
                [
                    # Card Header (Clickable to toggle justification)
                    html.Div(
                        [
                            html.H4(
                                f"{prediction['coin']}: {prediction['recommendation']}",
                                id=f"header-{idx}",
                                style={
                                    "color": prediction['color'],
                                    "fontSize": "1.5rem",
                                    "fontWeight": "bold",
                                    "fontFamily": "Montserrat, sans-serif",
                                    "textAlign": "center",
                                    "textShadow": f"0 0 8px {prediction['color']}",
                                    "margin": "0",
                                    "cursor": "pointer",
                                    "transition": "all 0.3s ease"
                                }
                            )
                        ],
                        style={
                            "padding": "15px",
                            "borderBottom": f"1px solid {prediction['color']}",
                            "background": f"linear-gradient(145deg, {obsidian_black}, {sapphire_blue})"
                        }
                    ),
                    # Collapsible Justification
                    html.Div(
                        id=justification_id,
                        children=[
                            html.P(
                                prediction['justification'],
                                style={
                                    "color": platinum_silver,
                                    "fontSize": "0.9rem",
                                    "fontFamily": "Open Sans, sans-serif",
                                    "textAlign": "center",
                                    "margin": "10px",
                                    "lineHeight": "1.4"
                                }
                            )
                        ],
                        style={
                            "display": "none",  # Initially hidden
                            "padding": "10px",
                            "background": obsidian_black
                        }
                    )
                ],
                style={
                    "background": f"linear-gradient(145deg, {obsidian_black}, {sapphire_blue})",
                    "border": f"2px solid {prediction['color']}",
                    "borderRadius": "15px",
                    "margin": "15px",
                    "maxWidth": "300px",
                    "boxShadow": f"0 0 20px {prediction['color']}80, inset 0 0 10px {prediction['color']}40",
                    "transition": "transform 0.3s ease, box-shadow 0.3s ease",
                    "cursor": "default",
                    ":hover": {
                        "transform": "translateY(-5px)",
                        "boxShadow": f"0 0 30px {prediction['color']}, inset 0 0 15px {prediction['color']}80"
                    }
                },
                className="prediction-card"
            )
        )

        # Client-side callback for toggling justification
        clientside_callback(
            f"""
            function(n_clicks) {{
                const justification = document.getElementById('{justification_id}');
                if (justification.style.display === 'none') {{
                    justification.style.display = 'block';
                }} else {{
                    justification.style.display = 'none';
                }}
                return window.dash_clientside.no_update;
            }}
            """,
            Output(justification_id, "style", allow_duplicate=True),
            Input(f"header-{idx}", "n_clicks"),
            prevent_initial_call=True
        )

    return html.Div(
        prediction_cards,
        style={
            "display": "grid",
            "gridTemplateColumns": "repeat(auto-fit, minmax(300px, 1fr))",
            "gap": "20px",
            "justifyItems": "center",
            "padding": "20px",
            "margin": "0 auto",
            "maxWidth": "1200px"
        }
    )

layout = html.Div([
    html.H1("Crypto Social Media", style={
        "fontSize": "4rem",
        "fontWeight": "700",
        "color": platinum_silver,
        "textAlign": "center",
        "textShadow": f"0 0 20px {theme_color}, 0 0 40px {theme_color}",
        "marginTop": "80px",
        "marginBottom": "40px",
        "animation": "glowIn 2s ease forwards",
        "fontFamily": "Montserrat, sans-serif"
    }),
    
    html.P("Latest social media updates and investment predictions for cryptocurrencies", style={
        "fontSize": "1.5rem",
        "color": platinum_silver,
        "textAlign": "center",
        "marginBottom": "30px",
        "animation": "fadeIn 1.5s 0.5s forwards",
        "fontFamily": "Open Sans, sans-serif"
    }),
    
    html.Div(id="error-message-social", style={
        "color": crimson_red,
        "textAlign": "center",
        "fontSize": "1.2rem",
        "marginBottom": "20px",
        "fontFamily": "Open Sans, sans-serif"
    }),
    
    html.Div([
        dbc.Button("Refresh", id="refresh-social-button", color="info", style={
            "background": f"linear-gradient(45deg, {sapphire_blue}, {theme_color})",
            "border": "none",
            "color": obsidian_black,
            "padding": "10px 25px",
            "fontWeight": "bold",
            "borderRadius": "8px",
            "boxShadow": f"0 0 10px {theme_color}",
            "marginBottom": "20px",
            "transition": "all 0.3s ease",
            "fontFamily": "Montserrat, sans-serif",
            ":hover": {
                "boxShadow": f"0 0 20px {theme_color}, 0 0 30px {theme_color}80",
                "transform": "scale(1.05)"
            }
        })
    ], style={"textAlign": "center"}),
    
    html.Div(id="social-media-table-container", style={"marginBottom": "40px"}),
    
    html.Div(id="investment-prediction-container", style={"marginBottom": "40px"}),
    
    dcc.Interval(id="interval-social-component", interval=60*1000, n_intervals=0),
    dcc.Store(id="social-media-store", data=load_cache())
])

@dash.callback(
    [Output("social-media-store", "data"),
     Output("social-media-table-container", "children"),
     Output("investment-prediction-container", "children"),
     Output("error-message-social", "children")],
    [Input("interval-social-component", "n_intervals"),
     Input("refresh-social-button", "n_clicks")],
    [State("social-media-store", "data")]
)
def update_social_data(n_intervals, n_clicks, stored_posts):
    n_clicks = n_clicks or 0

    if n_clicks > 0:
        stored_posts = []
        if os.path.exists(CACHE_FILE):
            os.remove(CACHE_FILE)
            print("Cache cleared.")

    if stored_posts is None:
        stored_posts = load_cache()
        if not stored_posts:
            stored_posts = []

    new_posts = fetch_new_social_media_posts()
    if not new_posts:
        return stored_posts, generate_social_media_table(stored_posts), predict_investment_model(stored_posts), "Error: Unable to fetch new social data."

    updated_posts = stored_posts + new_posts
    updated_posts = updated_posts[-50:]
    save_cache(updated_posts)

    table = generate_social_media_table(updated_posts)
    investment_prediction = predict_investment_model(updated_posts)

    return updated_posts, table, investment_prediction, ""