import praw
import pandas as pd
from transformers import pipeline
import dash
from dash import dcc, html, dash_table
from dash.dependencies import Input, Output
import plotly.express as px
from datetime import datetime
import time

# === Reddit API Connection ===
try:
    reddit = praw.Reddit(
        client_id='4WDJh4AzVCv11yLVVbONnw',
        client_secret='jCvSUFN0Dlc6dlTILNYgDXPYLB1LTw',
        user_agent='script:sentiment-test:v1.0 (by /u/omarbenmansour)'
    )
    print("Reddit connection successful. Read-only mode:", reddit.read_only)
except Exception as auth_error:
    print(f"Authentication failed: {auth_error}")
    exit()

# Initialize Dash app
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Bitcoin Sentiment Dashboard", style={'textAlign': 'center', 'color': '#1E90FF'}),
    
    dcc.Interval(
        id='interval-component',
        interval=30*60*1000,  # Update every 30 minutes
        n_intervals=0
    ),
    
    html.Div(id='last-updated'),
    
    dcc.Tabs([
        dcc.Tab(label='Sentiment Overview', children=[
            html.Div([
                dcc.Graph(id='sentiment-pie'),
                dcc.Graph(id='sentiment-bar')
            ], style={'display': 'flex'})
        ]),
        
        dcc.Tab(label='Post Analysis', children=[
            html.Div([
                dcc.Graph(id='posts-timeline'),
                dash_table.DataTable(
                    id='posts-table',
                    columns=[
                        {'name': 'Title', 'id': 'title'},
                        {'name': 'Sentiment', 'id': 'sentiment_name'},
                        {'name': 'Upvotes', 'id': 'score'},
                        {'name': 'Date', 'id': 'date'}
                    ],
                    style_table={'overflowX': 'auto'},
                    style_cell={
                        'textAlign': 'left',
                        'padding': '10px',
                        'whiteSpace': 'normal',
                        'height': 'auto'
                    },
                    page_size=10
                )
            ])
        ])
    ]),
    
    html.Div([
        html.Button("Refresh Data", id='refresh-button', n_clicks=0),
        html.Div(id='refresh-message')
    ], style={'margin-top': '20px'})
], style={'padding': '20px'})

# Callback to update all data
@app.callback(
    [Output('sentiment-pie', 'figure'),
     Output('sentiment-bar', 'figure'),
     Output('posts-timeline', 'figure'),
     Output('posts-table', 'data'),
     Output('last-updated', 'children')],
    [Input('interval-component', 'n_intervals'),
     Input('refresh-button', 'n_clicks')]
)
def update_dashboard(n_intervals, n_clicks):
    # Get current time for update message
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        # === Data Collection ===
        posts = []
        for post in reddit.subreddit("CryptoCurrency").hot(limit=50):
            if "bitcoin" in post.title.lower():
                posts.append({
                    "title": post.title,
                    "content": post.selftext,
                    "created_utc": post.created_utc,
                    "score": post.score
                })
        
        if not posts:
            return [px.pie(), px.bar(), px.scatter(), [], f"Last updated: {current_time} (No posts found)"]
        
        # === Create DataFrame ===
        df = pd.DataFrame(posts)
        df["text"] = df["title"] + " " + df["content"]
        df["clean_text"] = df["text"].str[:512].str.replace(r'[^\w\s]', '', regex=True)
        
        # === Sentiment Analysis ===
        sentiment_model = pipeline(
            "sentiment-analysis",
            model="cardiffnlp/twitter-roberta-base-sentiment",
            device="cpu"
        )
        
        df["sentiment"] = df["clean_text"].apply(
            lambda x: sentiment_model(x[:100])[0]['label']
        )
        
        # Map sentiment labels
        label_map = {'LABEL_0': 'Negative', 'LABEL_1': 'Neutral', 'LABEL_2': 'Positive'}
        df['sentiment_name'] = df['sentiment'].map(label_map)
        df['date'] = pd.to_datetime(df['created_utc'], unit='s')
        
        # === Create Visualizations ===
        # Pie Chart
        pie_fig = px.pie(
            df, 
            names='sentiment_name',
            title='Sentiment Distribution',
            color='sentiment_name',
            color_discrete_map={'Negative': 'red', 'Neutral': 'gray', 'Positive': 'green'},
            hole=0.3
        )
        
        # Bar Chart
        bar_fig = px.bar(
            df['sentiment_name'].value_counts().reset_index(),
            x='sentiment_name',
            y='count',
            title='Sentiment Count',
            color='sentiment_name',
            color_discrete_map={'Negative': 'red', 'Neutral': 'gray', 'Positive': 'green'}
        )
        bar_fig.update_layout(xaxis_title='Sentiment', yaxis_title='Count')
        
        # Timeline
        timeline_fig = px.scatter(
            df,
            x='date',
            y='score',
            color='sentiment_name',
            hover_data=['title'],
            title='Post Activity Timeline',
            color_discrete_map={'Negative': 'red', 'Neutral': 'gray', 'Positive': 'green'}
        )
        timeline_fig.update_layout(
            xaxis_title='Date',
            yaxis_title='Upvotes',
            hovermode='closest'
        )
        
        # Prepare table data
        table_data = df.sort_values('score', ascending=False)[['title', 'sentiment_name', 'score', 'date']].to_dict('records')
        
        return [pie_fig, bar_fig, timeline_fig, table_data, f"Last updated: {current_time} | {len(df)} posts analyzed"]
    
    except Exception as e:
        print(f"Error updating dashboard: {e}")
        return [px.pie(), px.bar(), px.scatter(), [], f"Last updated: {current_time} (Error occurred)"]

@app.callback(
    Output('refresh-message', 'children'),
    [Input('refresh-button', 'n_clicks')]
)
def show_refresh_message(n_clicks):
    if n_clicks > 0:
        return "Refreshing data..."
    return ""

if __name__ == '__main__':
    app.run(debug=True, port=8050)