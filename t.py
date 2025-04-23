import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import base64
import os
from datetime import datetime
from pymongo import MongoClient
import pandas as pd
from pptx import Presentation
from io import BytesIO
import pdfplumber
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
import ollama

# MongoDB Setup
client = MongoClient("mongodb://localhost:27017/")
db = client["due_diligence"]
collection = db["qa_sessions"]

MODEL_NAME = "mistral:latest"

# Dash App Setup
app = dash.Dash(__name__, external_stylesheets=[dbc.themes.BOOTSTRAP])
app.title = "Due Diligence ChatBot"

navbar = dbc.NavbarSimple(
    brand="Due Diligence Assistant",
    brand_href="#",
    color="dark",
    dark=True,
    children=[
        dbc.NavItem(dbc.NavLink("Home", href="#home")),
        dbc.NavItem(dbc.NavLink("Chat", href="#chat")),
        dbc.NavItem(dbc.NavLink("Export", href="#export")),
    ]
)

app.layout = html.Div([
    navbar,
    html.Div(id='home', children=[
        dbc.Container([
            html.H2("Welcome to the Due Diligence Assistant", className="my-4"),
            html.P("Upload a document, ask questions, get insights.")
        ])
    ], style={"padding": "2rem"}),

    html.Div(id='chat', children=[
        dbc.Container([
            dcc.Upload(
                id='upload-data',
                children=html.Div(['Drag and Drop or ', html.A('Select a File')]),
                style={
                    'width': '100%', 'height': '60px', 'lineHeight': '60px',
                    'borderWidth': '1px', 'borderStyle': 'dashed',
                    'borderRadius': '5px', 'textAlign': 'center'
                },
                multiple=False
            ),
            html.Br(),
            dcc.Textarea(id='context-area', style={'width': '100%', 'height': 200}),
            html.Br(),
            dcc.Input(id='user-question', type='text', placeholder='Ask a question...', style={'width': '80%'}),
            html.Button('Submit', id='submit-question', n_clicks=0),
            html.Br(), html.Br(),
            html.Div(id='answer-area')
        ])
    ], style={"padding": "2rem"}),

    html.Div(id='export', children=[
        dbc.Container([
            html.H4("Export Your Conversation"),
            html.Button("Download CSV", id="download-csv-btn"),
            dcc.Download(id="download-csv")
        ])
    ], style={"padding": "2rem"})
])

# Helper Functions

def extract_text_from_pdf(contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    with pdfplumber.open(BytesIO(decoded)) as pdf:
        text = "\n".join([page.extract_text() for page in pdf.pages if page.extract_text()])
    return text

def find_relevant_context(question, context_text, max_words=300):
    vectorizer = TfidfVectorizer(stop_words="english")
    corpus = [context_text, question]
    tfidf_matrix = vectorizer.fit_transform(corpus)
    similarity_scores = (tfidf_matrix[-1] @ tfidf_matrix[:-1].T).toarray()[0]
    return context_text[:max_words] if similarity_scores[0] > 0 else ""

def generate_answer_with_ollama(question, context):
    prompt = f"""
    You are a due diligence expert. Use the context to answer the question.

    CONTEXT:
    {context}

    QUESTION:
    {question}

    ANSWER:
    """
    response = ollama.chat(model=MODEL_NAME, messages=[{"role": "user", "content": prompt}], options={"num_predict": 250})
    return response['message']['content'].strip()

# Callbacks
@app.callback(
    Output('context-area', 'value'),
    Input('upload-data', 'contents')
)
def update_context_area(contents):
    if contents:
        return extract_text_from_pdf(contents)
    return ''

@app.callback(
    Output('answer-area', 'children'),
    Input('submit-question', 'n_clicks'),
    State('user-question', 'value'),
    State('context-area', 'value')
)
def handle_question(n_clicks, question, context):
    if n_clicks and question:
        relevant_context = find_relevant_context(question, context)
        answer = generate_answer_with_ollama(question, relevant_context)
        return html.Div([
            html.H5("Answer:"),
            html.P(answer)
        ])
    return ''

@app.callback(
    Output("download-csv", "data"),
    Input("download-csv-btn", "n_clicks"),
    prevent_initial_call=True
)
def download_csv(n_clicks):
    data = list(collection.find({}, {"_id": 0, "session": 1, "messages": 1}))
    df = pd.DataFrame(data)
    return dcc.send_data_frame(df.to_csv, filename="qa_history.csv")

if __name__ == '__main__':
    app.run_server(debug=True)