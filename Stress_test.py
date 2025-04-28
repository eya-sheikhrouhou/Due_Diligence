import dash
from dash import dcc, html, Input, Output
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from statsmodels.tsa.arima.model import ARIMA
import os

# === 1. Chargement dynamique du fichier sélectionné ===
FOLDER_PATH = "C:/Users/omarb/OneDrive/Bureau/PI/DATA/LOT3"

available_files = [f for f in os.listdir(FOLDER_PATH) if f.endswith(".csv")]

# === 2. App ===
app = dash.Dash(__name__)
server = app.server

app.layout = html.Div([
    html.H1("📊 Stress Test + Prédiction - Crypto Due Diligence"),

    html.Label("📁 Sélection de crypto (CSV):"),
    dcc.Dropdown(
        id='file-selector',
        options=[{'label': f.split(' ')[0], 'value': f} for f in available_files],
        value=available_files[0],
        style={'width': '50%'}
    ),

    html.Label("💥 Choc simulé (% de baisse):"),
    dcc.Slider(id='drop-slider', min=10, max=90, step=5, value=30,
               marks={i: f"{i}%" for i in range(10, 95, 10)}),

    html.Label("📆 Jour du stress (index temporel):"),
    dcc.Slider(id='shock-slider', min=10, max=90, step=1, value=70),

    html.Label("🔮 Prédire les prochains jours :"),
    dcc.Slider(id='forecast-days', min=1, max=30, step=1, value=7,
               marks={i: str(i) for i in range(1, 31, 5)}),

    html.Label("📅 Afficher les X derniers jours :"),
    dcc.Slider(id='lookback-days', min=30, max=365, step=30, value=90,
               marks={i: f"{i}j" for i in range(30, 366, 30)}),

    html.Br(),
    html.Div(id='resilience-score', style={'fontSize': 24, 'fontWeight': 'bold'}),
    dcc.Graph(id='stress-graph'),
    html.Div(id='analysis-output', style={'marginTop': 30, 'fontSize': 18})
])

# === 3. Callback ===
@app.callback(
    [Output('stress-graph', 'figure'),
     Output('resilience-score', 'children'),
     Output('analysis-output', 'children'),
     Output('shock-slider', 'max')],
    [Input('file-selector', 'value'),
     Input('drop-slider', 'value'),
     Input('shock-slider', 'value'),
     Input('forecast-days', 'value'),
     Input('lookback-days', 'value')]
)
def update_output(file, drop_pct, shock_day, forecast_days, lookback_days):
    filepath = os.path.join(FOLDER_PATH, file)
    df = pd.read_csv(filepath)
    df.columns = [col.strip().replace('"', '') for col in df.columns]
    df['Date'] = pd.to_datetime(df['Date'], format='%m/%d/%Y', errors='coerce')
    df = df.dropna(subset=['Date'])
    df['Price'] = df['Price'].astype(str).str.replace(',', '').astype(float)
    df = df.sort_values('Date')
    df.set_index('Date', inplace=True)
    df = df[['Price']].rename(columns={"Price": "CRYPTO"})

    # Filtrer selon la fenêtre lookback
    df = df.last(f'{lookback_days}D')

    # Stress test
    stressed_df = df.copy()
    if shock_day < len(df):
        stress_date = df.index[shock_day]
        stressed_df.loc[stress_date:, 'CRYPTO'] *= (1 - drop_pct / 100)
    else:
        stress_date = df.index[-1]

    drop = 1 - stressed_df['CRYPTO'].iloc[-1] / df['CRYPTO'].iloc[-1]
    score = max(0, 100 - 100 * drop)
    score_text = f"🛡️ Score de Résilience : {round(score, 2)} / 100"

    if score > 75:
        analysis = "✅ Résilience forte face aux chocs."
    elif score > 50:
        analysis = "⚠️ Résilience modérée. Couverture conseillée."
    else:
        analysis = "🚨 Faible résilience. Risque élevé."

    # Prédiction ARIMA pour la série originale
    model = ARIMA(df['CRYPTO'], order=(5, 1, 0))
    fitted = model.fit()
    forecast = fitted.forecast(steps=forecast_days)
    forecast_index = pd.date_range(start=df.index[-1] + pd.Timedelta(days=1), periods=forecast_days, freq='D')
    forecast_df = pd.DataFrame({"Prévision": forecast.values}, index=forecast_index)

    # Prédiction ARIMA pour la série stressée
    stressed_model = ARIMA(stressed_df['CRYPTO'], order=(5, 1, 0))
    stressed_fit = stressed_model.fit()
    stressed_forecast = stressed_fit.forecast(steps=forecast_days)
    stressed_forecast_df = pd.DataFrame({"Prévision Stressée": stressed_forecast.values}, index=forecast_index)

    # Étendre les limites du graphe
    full_index = df.index.union(forecast_index)

    # Graphique
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df.index, y=df['CRYPTO'], mode='lines', name='Original'))
    fig.add_trace(go.Scatter(x=stressed_df.index, y=stressed_df['CRYPTO'], mode='lines', name='Stressé'))
    fig.add_trace(go.Scatter(x=forecast_df.index, y=forecast_df['Prévision'], mode='lines', name='Prévision', line=dict(dash='dot')))
    fig.add_trace(go.Scatter(x=stressed_forecast_df.index, y=stressed_forecast_df['Prévision Stressée'], mode='lines', name='Prévision Stressée', line=dict(dash='dot', color='red')))
    fig.add_shape(type='line', x0=stress_date, x1=stress_date,
                  y0=stressed_df['CRYPTO'].min(), y1=stressed_df['CRYPTO'].max(),
                  line=dict(color="red", dash="dash"))
    fig.add_annotation(x=stress_date, y=df['CRYPTO'].max(), text="Choc", showarrow=True)
    fig.update_layout(title="Impact + Prévision", xaxis_title="Date", yaxis_title="Prix", height=600,
                      xaxis=dict(range=[full_index.min(), full_index.max()]))

    return fig, score_text, analysis, len(df) - 10

if __name__ == '__main__':
    app.run(debug=True)
