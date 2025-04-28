import dash
from dash import dcc, html, Input, Output, callback, dash_table
import plotly.graph_objs as go
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import dash_bootstrap_components as dbc
from collections import deque
import time
import threading
import websockets
import asyncio
import json
from transformers import pipeline
from sklearn.preprocessing import MinMaxScaler

# Initialize the app with professional theme
app = dash.Dash(__name__, 
                external_stylesheets=[dbc.themes.DARKLY],
                meta_tags=[{'name': 'viewport',
                           'content': 'width=device-width, initial-scale=1.0'}])
server = app.server

# Configuration
CRYPTO_PAIRS = ['BTC-USD', 'ETH-USD', 'SOL-USD', 'ADA-USD', 'DOT-USD']
SOCIAL_SOURCES = ['Twitter', 'Reddit', 'Telegram', '4chan', 'Discord']
MAX_DATA_POINTS = 500  # For performance optimization

# Real-time data buffers
price_data = {pair: deque(maxlen=MAX_DATA_POINTS) for pair in CRYPTO_PAIRS}
social_data = {pair: deque(maxlen=MAX_DATA_POINTS) for pair in CRYPTO_PAIRS}

# Sentiment analysis pipeline (would use fine-tuned model in production)
sentiment_analyzer = pipeline("sentiment-analysis", 
                             model="finiteautomata/bertweet-base-sentiment-analysis")

# Initialize with sample data
def initialize_sample_data():
    for pair in CRYPTO_PAIRS:
        for i in range(100):
            price_data[pair].append({
                'timestamp': datetime.now() - timedelta(minutes=100-i),
                'price': np.random.normal(50000, 5000) if pair == 'BTC-USD' 
                        else np.random.normal(3000, 300) if pair == 'ETH-USD'
                        else np.random.normal(100, 10),
                'volume': np.random.lognormal(10, 1)
            })
            
            social_data[pair].append({
                'timestamp': datetime.now() - timedelta(minutes=100-i),
                'source': np.random.choice(SOCIAL_SOURCES),
                'content': "Sample tweet about crypto",
                'sentiment': np.random.normal(0.1, 0.2),
                'volume': np.random.poisson(50)
            })

initialize_sample_data()

# WebSocket clients for real-time data
async def connect_to_crypto_exchange():
    # In production, connect to actual exchange WS
    while True:
        try:
            async with websockets.connect('wss://example-crypto-feed.com') as ws:
                while True:
                    data = await ws.recv()
                    data = json.loads(data)
                    pair = data['symbol']
                    price_data[pair].append({
                        'timestamp': datetime.now(),
                        'price': float(data['price']),
                        'volume': float(data['volume'])
                    })
        except Exception as e:
            print(f"WS Error: {e}")
            time.sleep(5)

async def connect_to_social_feed():
    # In production, connect to social media WS
    while True:
        try:
            async with websockets.connect('wss://example-social-feed.com') as ws:
                while True:
                    data = await ws.recv()
                    data = json.loads(data)
                    pair = data['symbol']
                    # Real sentiment analysis
                    sentiment = sentiment_analyzer(data['content'])[0]
                    social_data[pair].append({
                        'timestamp': datetime.now(),
                        'source': data['source'],
                        'content': data['content'],
                        'sentiment': 1 if sentiment['label'] == 'POS' else 
                                    -1 if sentiment['label'] == 'NEG' else 0,
                        'volume': 1  # Count of mentions
                    })
        except Exception as e:
            print(f"WS Error: {e}")
            time.sleep(5)

# Start WebSocket clients in background
def run_websockets():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(asyncio.gather(
        connect_to_crypto_exchange(),
        connect_to_social_feed()
    ))

threading.Thread(target=run_websockets, daemon=True).start()

# Professional dashboard layout
app.layout = dbc.Container([
    # Header with logo and refresh indicator
    dbc.Row([
        dbc.Col(html.Div([
            html.Img(src="/assets/logo.png", height="40px", className="me-2"),
            html.H2("Crypto-Sentiment Pro", className="d-inline"),
            html.Small("Live", id="live-indicator", 
                      className="badge bg-danger ms-2")
        ], className="d-flex align-items-center"), width=8),
        dbc.Col(html.Div(id="last-updated", className="text-end"), width=4)
    ], className="my-3"),
    
    # Control panel
    dbc.Row([
        dbc.Col([
            html.Label("Asset Pair", className="form-label"),
            dcc.Dropdown(
                id='crypto-pair',
                options=[{'label': pair, 'value': pair} for pair in CRYPTO_PAIRS],
                value='BTC-USD',
                clearable=False,
                className="border-primary"
            )
        ], md=3),
        dbc.Col([
            html.Label("Timeframe", className="form-label"),
            dcc.Dropdown(
                id='timeframe',
                options=[
                    {'label': '5 Min', 'value': 5},
                    {'label': '15 Min', 'value': 15},
                    {'label': '1 Hour', 'value': 60},
                    {'label': '4 Hours', 'value': 240},
                    {'label': '1 Day', 'value': 1440}
                ],
                value=60,
                clearable=False,
                className="border-primary"
            )
        ], md=2),
        dbc.Col([
            html.Label("Social Sources", className="form-label"),
            dcc.Dropdown(
                id='social-sources',
                options=[{'label': 'All', 'value': 'all'}] + 
                       [{'label': src, 'value': src} for src in SOCIAL_SOURCES],
                value='all',
                multi=True,
                className="border-primary"
            )
        ], md=3),
        dbc.Col([
            html.Label("Alert Threshold", className="form-label"),
            dcc.Slider(
                id='alert-threshold',
                min=-1,
                max=1,
                step=0.1,
                value=0.3,
                marks={i: str(i) for i in [-1, -0.5, 0, 0.5, 1]},
                className="mt-2"
            )
        ], md=4)
    ], className="mb-4"),
    
    # Key metrics row
    dbc.Row([
        dbc.Col(dbc.Card([
            dbc.CardHeader("Price Change"),
            dbc.CardBody([
                html.H4(id="price-change", className="card-title"),
                html.P("vs previous period", className="card-text text-muted")
            ], className="text-center")
        ], color="primary", outline=True), md=2),
        dbc.Col(dbc.Card([
            dbc.CardHeader("Sentiment Score"),
            dbc.CardBody([
                html.H4(id="sentiment-score", className="card-title"),
                html.P(id="sentiment-change", className="card-text")
            ], className="text-center")
        ], color="info", outline=True), md=2),
        dbc.Col(dbc.Card([
            dbc.CardHeader("Correlation"),
            dbc.CardBody([
                html.H4(id="correlation-score", className="card-title"),
                html.P("Price-Sentiment", className="card-text text-muted")
            ], className="text-center")
        ], color="success", outline=True), md=2),
        dbc.Col(dbc.Card([
            dbc.CardHeader("Social Volume"),
            dbc.CardBody([
                html.H4(id="social-volume", className="card-title"),
                html.P(id="volume-change", className="card-text")
            ], className="text-center")
        ], color="warning", outline=True), md=2),
        dbc.Col(dbc.Card([
            dbc.CardHeader("Market Alert"),
            dbc.CardBody([
                html.H4(id="market-alert", className="card-title"),
                html.P(id="alert-message", className="card-text")
            ], className="text-center")
        ], color="danger", id="alert-card"), md=4)
    ], className="mb-4"),
    
    # Main charts
    dbc.Row([
        dbc.Col(dcc.Graph(id='price-sentiment-chart'), lg=6),
        dbc.Col(dcc.Graph(id='sentiment-heatmap'), lg=6)
    ]),
    dbc.Row([
        dbc.Col(dcc.Graph(id='volume-correlation-chart'), lg=6),
        dbc.Col(dcc.Graph(id='source-impact-chart'), lg=6)
    ]),
    
    # Data tables and advanced analytics
    dbc.Row([
        dbc.Col([
            html.H5("Recent Social Mentions", className="mt-3"),
            dash_table.DataTable(
                id='social-mentions-table',
                columns=[
                    {'name': 'Time', 'id': 'timestamp'},
                    {'name': 'Source', 'id': 'source'},
                    {'name': 'Sentiment', 'id': 'sentiment'},
                    {'name': 'Content', 'id': 'content', 'presentation': 'markdown'}
                ],
                style_table={'overflowX': 'auto'},
                style_cell={
                    'height': 'auto',
                    'minWidth': '100px', 'width': '150px', 'maxWidth': '300px',
                    'whiteSpace': 'normal',
                    'textAlign': 'left'
                },
                style_header={
                    'backgroundColor': 'rgb(30, 30, 30)',
                    'color': 'white',
                    'fontWeight': 'bold'
                },
                style_data={
                    'backgroundColor': 'rgb(50, 50, 50)',
                    'color': 'white'
                },
                page_size=5,
                filter_action='native',
                sort_action='native'
            )
        ], lg=6),
        dbc.Col([
            html.H5("Technical Indicators", className="mt-3"),
            dcc.Graph(id='technical-indicators'),
            dcc.Interval(id='ta-update', interval=10*1000)
        ], lg=6)
    ]),
    
    # Hidden div for triggering callbacks
    html.Div(id='hidden-div', style={'display': 'none'}),
    
    # Update interval
    dcc.Interval(
        id='interval-component',
        interval=5*1000,  # 5 seconds
        n_intervals=0
    )
], fluid=True, className="dbc")

# Callbacks for real-time updates
@app.callback(
    [Output('price-sentiment-chart', 'figure'),
     Output('sentiment-heatmap', 'figure'),
     Output('volume-correlation-chart', 'figure'),
     Output('source-impact-chart', 'figure'),
     Output('technical-indicators', 'figure'),
     Output('price-change', 'children'),
     Output('sentiment-score', 'children'),
     Output('correlation-score', 'children'),
     Output('social-volume', 'children'),
     Output('market-alert', 'children'),
     Output('alert-message', 'children'),
     Output('sentiment-change', 'children'),
     Output('volume-change', 'children'),
     Output('social-mentions-table', 'data'),
     Output('last-updated', 'children'),
     Output('live-indicator', 'className')],
    [Input('crypto-pair', 'value'),
     Input('timeframe', 'value'),
     Input('social-sources', 'value'),
     Input('alert-threshold', 'value'),
     Input('interval-component', 'n_intervals')]
)
def update_all(pair, timeframe, sources, threshold, n):
    # Get current data
    current_time = datetime.now()
    time_threshold = current_time - timedelta(minutes=timeframe)
    
    # Filter price data
    price_df = pd.DataFrame(price_data[pair])
    price_df = price_df[price_df['timestamp'] >= time_threshold]
    
    # Filter social data
    social_df = pd.DataFrame(social_data[pair])
    social_df = social_df[social_df['timestamp'] >= time_threshold]
    if sources != 'all' and isinstance(sources, list):
        social_df = social_df[social_df['source'].isin(sources)]
    
    # Calculate metrics
    price_change = 0
    if len(price_df) > 1:
        price_change = ((price_df['price'].iloc[-1] - price_df['price'].iloc[0]) / 
                       price_df['price'].iloc[0]) * 100
    
    sentiment_score = social_df['sentiment'].mean() if not social_df.empty else 0
    sentiment_change = ""
    if len(social_df) > 10:  # Enough data for comparison
        prev_sentiment = social_df['sentiment'].iloc[-10:-5].mean()
        curr_sentiment = social_df['sentiment'].iloc[-5:].mean()
        sentiment_change = f"{(curr_sentiment - prev_sentiment):+.2f} change"
    
    # Calculate correlation
    correlation = 0
    if not price_df.empty and not social_df.empty:
        merged = pd.merge(
            price_df.groupby(pd.Grouper(key='timestamp', freq='1min'))['price'].mean(),
            social_df.groupby(pd.Grouper(key='timestamp', freq='1min'))['sentiment'].mean(),
            left_index=True, right_index=True, how='outer'
        ).fillna(method='ffill').dropna()
        if len(merged) > 2:
            correlation = merged['price'].corr(merged['sentiment'])
    
    # Volume metrics
    social_vol = social_df['volume'].sum() if not social_df.empty else 0
    volume_change = ""
    if len(social_df) > 10:
        prev_vol = social_df['volume'].iloc[-10:-5].sum()
        curr_vol = social_df['volume'].iloc[-5:].sum()
        volume_change = f"{(curr_vol - prev_vol)/prev_vol*100:+.1f}%"
    
    # Market alerts
    alert_level = "Normal"
    alert_message = "No significant alerts"
    if abs(sentiment_score) > threshold:
        alert_level = "Warning" if sentiment_score > 0 else "Critical"
        alert_message = ("Strong positive sentiment detected" if sentiment_score > 0 
                        else "Strong negative sentiment detected")
    
    # Create charts
    price_sentiment_fig = create_price_sentiment_chart(price_df, social_df)
    sentiment_heatmap = create_sentiment_heatmap(social_df)
    volume_corr_fig = create_volume_correlation_chart(price_df, social_df)
    source_impact_fig = create_source_impact_chart(social_df)
    technical_fig = create_technical_indicators(price_df)
    
    # Prepare social mentions table data
    table_data = social_df.sort_values('timestamp', ascending=False).head(5)
    table_data = table_data.to_dict('records')
    
    # Update time indicator
    last_updated = f"Last update: {current_time.strftime('%H:%M:%S')}"
    live_class = "badge bg-danger blink" if n % 2 == 0 else "badge bg-danger"
    
    return (price_sentiment_fig, sentiment_heatmap, volume_corr_fig, 
            source_impact_fig, technical_fig,
            f"{price_change:+.2f}%", 
            f"{sentiment_score:.2f}", 
            f"{correlation:.2f}", 
            f"{social_vol:,}",
            alert_level,
            alert_message,
            sentiment_change,
            volume_change,
            table_data,
            last_updated,
            live_class)

def create_price_sentiment_chart(price_df, social_df):
    fig = go.Figure()
    
    # Price trace
    fig.add_trace(go.Scatter(
        x=price_df['timestamp'],
        y=price_df['price'],
        name='Price',
        line=dict(color='#00FFFF', width=2),
        yaxis='y1'
    ))
    
    # Sentiment trace (if data exists)
    if not social_df.empty:
        sentiment_agg = social_df.groupby(pd.Grouper(key='timestamp', freq='1min'))['sentiment'].mean()
        fig.add_trace(go.Scatter(
            x=sentiment_agg.index,
            y=sentiment_agg.values,
            name='Sentiment',
            line=dict(color='#FF69B4', width=2),
            yaxis='y2'
        ))
    
    fig.update_layout(
        title='Price & Sentiment Trend',
        yaxis=dict(title='Price (USD)', side='left'),
        yaxis2=dict(title='Sentiment Score', side='right', overlaying='y'),
        xaxis=dict(title='Time'),
        hovermode='x unified',
        template='plotly_dark',
        legend=dict(orientation='h', y=1.1),
        margin=dict(l=50, r=50, b=50, t=50, pad=4)
    )
    return fig

def create_sentiment_heatmap(social_df):
    if social_df.empty:
        return go.Figure()
    
    # Prepare data for heatmap
    social_df['time_bucket'] = social_df['timestamp'].dt.floor('5min')
    heatmap_data = social_df.groupby(['time_bucket', 'source'])['sentiment'].mean().unstack()
    
    fig = go.Figure(go.Heatmap(
        x=heatmap_data.index,
        y=heatmap_data.columns,
        z=heatmap_data.values.T,
        colorscale='RdYlGn',
        zmid=0,
        colorbar=dict(title='Sentiment')
    ))
    
    fig.update_layout(
        title='Sentiment Heatmap by Source',
        xaxis_title='Time',
        yaxis_title='Source',
        template='plotly_dark'
    )
    return fig

def create_volume_correlation_chart(price_df, social_df):
    fig = go.Figure()
    
    if not price_df.empty and not social_df.empty:
        # Aggregate to common time buckets
        price_vol = price_df.groupby(pd.Grouper(key='timestamp', freq='5min'))['volume'].sum()
        social_vol = social_df.groupby(pd.Grouper(key='timestamp', freq='5min'))['volume'].sum()
        
        common_index = price_vol.index.intersection(social_vol.index)
        if len(common_index) > 0:
            fig.add_trace(go.Scatter(
                x=social_vol[common_index],
                y=price_vol[common_index],
                mode='markers',
                marker=dict(
                    size=10,
                    color=social_df.groupby(pd.Grouper(key='timestamp', freq='5min'))['sentiment'].mean()[common_index],
                    colorscale='Viridis',
                    showscale=True,
                    colorbar=dict(title='Sentiment')
                ),
                name='Volume Correlation'
            ))
    
    fig.update_layout(
        title='Social Volume vs Trading Volume',
        xaxis_title='Social Volume',
        yaxis_title='Trading Volume',
        template='plotly_dark'
    )
    return fig

def create_source_impact_chart(social_df):
    fig = go.Figure()
    
    if not social_df.empty:
        for source in social_df['source'].unique():
            source_data = social_df[social_df['source'] == source]
            fig.add_trace(go.Violin(
                y=source_data['sentiment'],
                name=source,
                box_visible=True,
                meanline_visible=True,
                points="all",
                jitter=0.1
            ))
    
    fig.update_layout(
        title='Sentiment Distribution by Source',
        yaxis_title='Sentiment Score',
        template='plotly_dark'
    )
    return fig

def create_technical_indicators(price_df):
    fig = go.Figure()
    
    if len(price_df) > 20:  # Enough data for technical indicators
        # Calculate simple moving averages
        price_df['SMA_10'] = price_df['price'].rolling(window=10).mean()
        price_df['SMA_20'] = price_df['price'].rolling(window=20).mean()
        
        # Price trace
        fig.add_trace(go.Scatter(
            x=price_df['timestamp'],
            y=price_df['price'],
            name='Price',
            line=dict(color='#00FFFF', width=2)
        ))
        
        # SMA traces
        fig.add_trace(go.Scatter(
            x=price_df['timestamp'],
            y=price_df['SMA_10'],
            name='SMA 10',
            line=dict(color='orange', width=1)
        ))
        
        fig.add_trace(go.Scatter(
            x=price_df['timestamp'],
            y=price_df['SMA_20'],
            name='SMA 20',
            line=dict(color='purple', width=1)
        ))
    
    fig.update_layout(
        title='Technical Indicators',
        yaxis_title='Price',
        template='plotly_dark',
        showlegend=True
    )
    return fig

if __name__ == '__main__':
    app.run_server(debug=True, port=8050)