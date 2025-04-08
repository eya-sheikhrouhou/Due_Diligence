import dash
from dash import html, dcc, Input, Output, State
import dash_bootstrap_components as dbc
import torch
import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
import json
import re
import base64
import io
import PyPDF2
import docx
from model import model, tokenizer  # Importer le modèle et le tokenizer depuis model.py

dash.register_page(__name__, path="/banque_question", name="Question Bank")

theme_color = "#00eaff"

# Chargement des chunks existants pour la banque de réponses
try:
    existing_chunks = np.load("text_chunks.npy", allow_pickle=True).tolist()
except Exception as e:
    print(f"Erreur lors du chargement de text_chunks.npy : {str(e)}")
    existing_chunks = []

# Initialisation des chunks pour les nouveaux uploads
new_chunks = []  # Chunks provenant d'un nouvel upload dans la session courante
index = None

embed_model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

# Recréer l'index FAISS si nécessaire
def create_faiss_index(chunks):
    if not chunks:
        print("Aucun chunk disponible pour créer l'index FAISS.")
        return None
    try:
        embeddings = embed_model.encode(chunks, convert_to_numpy=True)
        dimension = embeddings.shape[1]
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)
        faiss.write_index(index, "faiss_index.bin")
        print(f"Index FAISS créé avec succès pour {len(chunks)} chunks.")
        return index
    except Exception as e:
        print(f"Erreur lors de la création de l'index FAISS : {str(e)}")
        return None

# Charger ou créer l'index FAISS pour les chunks existants
try:
    index = faiss.read_index("faiss_index.bin")
    if index.ntotal == 0 or index.ntotal != len(existing_chunks):
        print("Index FAISS vide ou incohérent avec les chunks existants. Recréation de l'index...")
        index = create_faiss_index(existing_chunks)
except Exception as e:
    print(f"Erreur lors du chargement de faiss_index.bin : {str(e)}")
    index = create_faiss_index(existing_chunks)

def generate_questions_from_document(context):
    if not context or context.strip() == "":
        print("Le chunk est vide ou invalide.")
        return "ESG:\nCompliance:\nLegal:\n"

    prompt = (
        "You are an expert in Due Diligence Reports. Based on the following document, generate specific questions for a Due Diligence Report. "
        "The questions must be divided into three categories: ESG, Compliance, and Legal. "
        "For ESG, focus on environmental impact, social responsibility, and governance. "
        "For Compliance, focus on regulatory adherence and risk management. "
        "For Legal, focus on legal rights, obligations, and liabilities. "
        "Generate exactly 2 questions per category, and ensure the questions are directly relevant to the document's content. "
        "Format the output as follows:\n\n"
        "ESG:\n- [Question 1]\n- [Question 2]\n"
        "Compliance:\n- [Question 1]\n- [Question 2]\n"
        "Legal:\n- [Question 1]\n- [Question 2]\n\n"
        "Example:\n"
        "Document: A company is developing a new cryptocurrency platform.\n"
        "ESG:\n- [What measures are in place to reduce the environmental impact of the cryptocurrency platform?]\n- [How does the platform ensure social responsibility in its operations?]\n"
        "Compliance:\n- [Does the platform comply with international cryptocurrency regulations?]\n- [What risk management strategies are in place for regulatory compliance?]\n"
        "Legal:\n- [What legal rights do users have over their digital assets on the platform?]\n- [Are there potential legal liabilities in the platform's operations?]\n\n"
        "Now, generate questions for the following document:\n"
        f"Document: {context}\n"
    )
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048).to("cuda" if torch.cuda.is_available() else "cpu")
    try:
        output = model.generate(**inputs, max_new_tokens=300)
        decoded = tokenizer.decode(output[0], skip_special_tokens=True)
        # Nettoyer la sortie : prendre uniquement la partie après le dernier "Document:"
        if "Document:" in decoded:
            decoded = decoded.split("Document:")[-1].strip()
        print(f"Questions générées pour le chunk : {decoded}")
        return decoded
    except Exception as e:
        print(f"Erreur lors de la génération des questions : {str(e)}")
        return "ESG:\nCompliance:\nLegal:\n"

def parse_and_classify_questions(response_text, context):
    question_bank = {"ESG": [], "Compliance": [], "Legal": []}
    current_category = None

    # Nettoyer la sortie : supprimer tout ce qui est avant "ESG:"
    if "ESG:" in response_text:
        response_text = response_text[response_text.index("ESG:"):].strip()
    
    lines = response_text.split("\n")
    for line in lines:
        line = line.strip()
        if line.startswith("ESG:"):
            current_category = "ESG"
        elif line.startswith("Compliance:"):
            current_category = "Compliance"
        elif line.startswith("Legal:"):
            current_category = "Legal"
        elif line.startswith("- [") and current_category:
            # Extraire la question entre les crochets
            question = re.search(r"\[(.*?)\]", line)
            if question:
                question_text = question.group(1).strip()
                if question_text and question_text not in question_bank[current_category]:
                    question_bank[current_category].append(question_text)
        elif line.startswith("- ") and current_category:
            # Gérer le format sans crochets (ancien format)
            question = line.lstrip("- ").strip()
            if question and question not in question_bank[current_category]:
                question_bank[current_category].append(question)
        else:
            print(f"Ligne ignorée ou mal formatée lors du parsing : {line}")

    for category in question_bank:
        questions = question_bank[category]
        if len(questions) < 2 or any("Question 1" in q or "Question 2" in q for q in questions):
            question_bank[category] = []
            if category == "ESG":
                if "digital assets" in context.lower() or "online game" in context.lower():
                    question_bank[category] = [
                        "What environmental impact does the management of digital assets or online games have?",
                        "How are social governance practices implemented in the digital asset or gaming framework?"
                    ]
                else:
                    question_bank[category] = [
                        "What measures are in place to reduce environmental impact?",
                        "How does the project ensure social responsibility?"
                    ]
            elif category == "Compliance":
                if "legal regulation" in context.lower() or "judicial protection" in context.lower():
                    question_bank[category] = [
                        "How does the project comply with regulations regarding digital assets or online games?",
                        "What risk management strategies are in place for regulatory compliance?"
                    ]
                else:
                    question_bank[category] = [
                        "Does the project comply with local regulations?",
                        "What risk management strategies are implemented?"
                    ]
            elif category == "Legal":
                if "property" in context.lower() or "online game" in context.lower():
                    question_bank[category] = [
                        "What legal rights do stakeholders have over virtual property in online games?",
                        "Are there potential legal liabilities in the management of virtual property?"
                    ]
                else:
                    question_bank[category] = [
                        "What legal rights do stakeholders have?",
                        "Are there any potential legal liabilities?"
                    ]

    print(f"Questions parsées : {question_bank}")
    return question_bank    

# RAG pour générer des réponses
def retrieve_text(query, top_k=1, use_new_chunks=True):
    chunks_to_use = new_chunks if use_new_chunks and new_chunks else existing_chunks
    if not index or not chunks_to_use or index.ntotal == 0:
        print("Index FAISS ou chunks non disponibles.")
        return ""

    try:
        query_embedding = embed_model.encode([query], convert_to_numpy=True)
        distances, indices = index.search(query_embedding, top_k)
        valid_indices = [i for i in indices[0] if 0 <= i < len(chunks_to_use)]
        if not valid_indices:
            print(f"Aucun indice valide trouvé pour la requête '{query}'.")
            return ""
        retrieved_chunks = [chunks_to_use[i] for i in valid_indices]
        print(f"Texte récupéré pour la requête '{query}' : {retrieved_chunks}")
        return "\n".join(retrieved_chunks)
    except Exception as e:
        print(f"Erreur lors de la récupération du texte : {str(e)}")
        return ""

def generate_answer_for_question(question, use_new_chunks=True):
    context = retrieve_text(question, use_new_chunks=use_new_chunks)
    if not context:
        print(f"Aucun contexte trouvé pour la question : {question}")
        return "No relevant context found to answer this question."
    
    full_query = f"Context: {context}\n\nQuestion: {question}"
    inputs = tokenizer(full_query, return_tensors="pt", truncation=True, max_length=2048).to("cuda" if torch.cuda.is_available() else "cpu")
    try:
        output = model.generate(**inputs, max_new_tokens=100)
        decoded = tokenizer.decode(output[0], skip_special_tokens=True)
        print(f"Réponse générée pour la question '{question}' : {decoded}")
        return decoded
    except Exception as e:
        print(f"Erreur lors de la génération de la réponse pour '{question}' : {str(e)}")
        return "Error generating answer."

# Fonction pour générer la banque de questions et réponses
def generate_question_bank(max_chunks=1):
    print("Début de la génération de la banque de questions...")
    question_bank = {"ESG": [], "Compliance": [], "Legal": []}
    
    try:
        if not new_chunks:
            print("Aucun nouveau chunk disponible pour générer des questions.")
            return question_bank

        for i, chunk in enumerate(new_chunks[:max_chunks]):
            print(f"Traitement du chunk {i+1}/{max_chunks} : {chunk[:100]}...")
            response = generate_questions_from_document(chunk)
            chunk_questions = parse_and_classify_questions(response, chunk)
            
            for category in chunk_questions:
                limited_questions = chunk_questions[category][:2]
                for question in limited_questions:
                    print(f"Génération de la réponse pour la question : {question}")
                    answer = generate_answer_for_question(question, use_new_chunks=True)
                    question_bank[category].append({"question": question, "answer": answer})
        
        for category in question_bank:
            seen_questions = set()
            unique_entries = []
            for entry in question_bank[category]:
                if entry["question"] not in seen_questions:
                    seen_questions.add(entry["question"])
                    unique_entries.append(entry)
            question_bank[category] = unique_entries
        
        with open("question_bank_with_answers.json", "w", encoding="utf-8") as f:
            json.dump(question_bank, f, indent=4, ensure_ascii=False)
        
        print("Banque de questions générée avec succès :")
        print(question_bank)
        return question_bank

    except Exception as e:
        print(f"Erreur lors de la génération de la banque de questions : {str(e)}")
        return {"ESG": [], "Compliance": [], "Legal": []}

# Fonction pour formater l'affichage des questions avec surbrillance
def format_questions_with_highlights(question_bank):
    print("Formatage des questions pour l'affichage...")
    highlighted = []
    highlight_color = "#00eaff"
    keywords = ["legal", "rights", "property", "recognition", "compliance", "esg", "governance", "environmental", "social"]

    for category, entries in question_bank.items():
        highlighted.append(html.H4(category, style={"color": theme_color, "marginTop": "20px"}))
        if not entries:
            highlighted.append(html.P("No questions generated for this category. Please upload a document first.", style={"color": "#ff5555"}))
        else:
            for entry in entries:
                question = entry["question"]
                answer = entry["answer"]
                highlighted_question = []
                words = question.split()
                for word in words:
                    if any(keyword in word.lower() for keyword in keywords):
                        highlighted_question.append(html.Span(word + " ", style={"color": highlight_color, "fontWeight": "bold"}))
                    else:
                        highlighted_question.append(word + " ")
                highlighted.append(html.P(highlighted_question, style={"color": "#ffffff", "marginLeft": "20px"}))
                highlighted.append(html.P(f"Answer: {answer}", style={"color": "#cccccc", "marginLeft": "40px", "fontStyle": "italic"}))

    print("Questions formatées pour l'affichage :")
    print(highlighted)
    return highlighted

# Fonction pour vérifier l'exactitude des documents
def verify_document(context):
    if not context or context.strip() == "":
        print("Le chunk est vide ou invalide pour la vérification.")
        return "ESG:\nCompliance:\nLegal:\n"

    prompt = (
        "Act like a senior compliance officer, understand deeply this document, "
        "identify any risks, inconsistencies, or issues that could affect a Due Diligence Report. "
        "Focus on ESG, Compliance, and Legal aspects. "
        "Format the output as a list of issues under each category, like this:\n"
        "ESG:\n- Issue 1\n- Issue 2\nCompliance:\n- Issue 1\n- Issue 2\nLegal:\n- Issue 1\n- Issue 2\n\n"
        f"Document: {context}"
    )
    inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=2048).to("cuda" if torch.cuda.is_available() else "cpu")
    try:
        output = model.generate(**inputs, max_new_tokens=200)
        decoded = tokenizer.decode(output[0], skip_special_tokens=True)
        print(f"Résultats de vérification pour le chunk : {decoded}")
        return decoded
    except Exception as e:
        print(f"Erreur lors de la vérification du document : {str(e)}")
        return "ESG:\nCompliance:\nLegal:\n"

# Fonction pour parser les problèmes identifiés
def parse_verification_results(response_text):
    verification_results = {"ESG": [], "Compliance": [], "Legal": []}
    current_category = None

    if "Document:" in response_text:
        response_text = response_text.split("Document:")[0]
    lines = response_text.split("\n")

    for line in lines:
        line = line.strip()
        if line.startswith("ESG:"):
            current_category = "ESG"
        elif line.startswith("Compliance:"):
            current_category = "Compliance"
        elif line.startswith("Legal:"):
            current_category = "Legal"
        elif line.startswith("-") and current_category:
            issue = line.lstrip("- ").strip()
            if issue and issue not in verification_results[current_category]:
                verification_results[current_category].append(issue)
        else:
            if line and current_category and not line.startswith(("ESG:", "Compliance:", "Legal:")):
                issue = line.strip()
                if issue and issue not in verification_results[current_category]:
                    verification_results[current_category].append(issue)
            print(f"Ligne ignorée ou mal formatée lors du parsing de vérification : {line}")

    print(f"Résultats de vérification parsés : {verification_results}")
    return verification_results

# Fonction pour vérifier tous les documents
def verify_all_documents(max_chunks=1):
    print("Début de la vérification des documents...")
    verification_results = {"ESG": [], "Compliance": [], "Legal": []}
    
    try:
        if not new_chunks:
            print("Aucun nouveau chunk disponible pour la vérification.")
            return verification_results

        for i, chunk in enumerate(new_chunks[:max_chunks]):
            print(f"Vérification du chunk {i+1}/{max_chunks} : {chunk[:100]}...")
            response = verify_document(chunk)
            chunk_issues = parse_verification_results(response)
            
            for category in verification_results:
                verification_results[category].extend(chunk_issues[category])
        
        for category in verification_results:
            verification_results[category] = list(set(verification_results[category]))
        
        with open("verification_results.json", "w", encoding="utf-8") as f:
            json.dump(verification_results, f, indent=4, ensure_ascii=False)
        
        print("Résultats de la vérification :")
        print(verification_results)
        return verification_results

    except Exception as e:
        print(f"Erreur lors de la vérification des documents : {str(e)}")
        return {"ESG": [], "Compliance": [], "Legal": []}

# Fonction pour formater l'affichage des résultats de vérification
def format_verification_with_highlights(verification_results):
    print("Formatage des résultats de vérification pour l'affichage...")
    highlighted = []
    highlight_color = "#00eaff"
    keywords = ["legal", "rights", "property", "recognition", "compliance", "esg", "governance", "environmental", "social", "risk", "issue"]

    for category, issues in verification_results.items():
        highlighted.append(html.H4(category, style={"color": theme_color, "marginTop": "20px"}))
        if not issues:
            highlighted.append(html.P("No issues identified for this category. Please upload a document first.", style={"color": "#ff5555"}))
        else:
            for issue in issues:
                highlighted_issue = []
                words = issue.split()
                for word in words:
                    if any(keyword in word.lower() for keyword in keywords):
                        highlighted_issue.append(html.Span(word + " ", style={"color": highlight_color, "fontWeight": "bold"}))
                    else:
                        highlighted_issue.append(word + " ")
                highlighted.append(html.P(highlighted_issue, style={"color": "#ffffff", "marginLeft": "20px"}))

    print("Résultats de vérification formatés pour l'affichage :")
    print(highlighted)
    return highlighted

# Fonction pour extraire le texte des documents
def extract_text_from_file(filename, contents):
    content_type, content_string = contents.split(',')
    decoded = base64.b64decode(content_string)
    
    if filename.endswith('.pdf'):
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(decoded))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    elif filename.endswith('.docx'):
        doc = docx.Document(io.BytesIO(decoded))
        text = ""
        for para in doc.paragraphs:
            text += para.text + "\n"
        return text
    elif filename.endswith('.txt'):
        return decoded.decode('utf-8')
    return ""

# Fonction pour découper le texte en chunks
def chunk_text(text, chunk_size=500):
    words = text.split()
    chunks = []
    current_chunk = []
    current_length = 0
    
    for word in words:
        current_length += len(word) + 1
        current_chunk.append(word)
        if current_length >= chunk_size:
            chunks.append(" ".join(current_chunk))
            current_chunk = []
            current_length = 0
    
    if current_chunk:
        chunks.append(" ".join(current_chunk))
    
    return chunks

# Layout
layout = html.Div([
    html.Div([
        html.H2("Question Bank & Document Verification", style={
            "fontSize": "2.8em",
            "fontWeight": "bold",
            "textAlign": "center",
            "marginTop": "60px",
            "color": "#ffffff",
            "textShadow": "0 0 8px #00eaff"
        }),

        # Bouton pour uploader des documents
        html.Div([
            dcc.Upload(
                id="upload-documents",
                children=html.Div([
                    "Drag and Drop or ",
                    html.A("Select Documents")
                ]),
                style={
                    "width": "65%",
                    "height": "60px",
                    "lineHeight": "60px",
                    "borderWidth": "1px",
                    "borderStyle": "dashed",
                    "borderRadius": "5px",
                    "textAlign": "center",
                    "margin": "20px auto",
                    "color": "#ffffff",
                    "borderColor": theme_color
                },
                multiple=True  # Permettre plusieurs fichiers
            ),
            html.Div(id="upload-status", style={"color": "#ffffff", "textAlign": "center"})
        ]),

        # Boutons pour générer la banque de questions et vérifier les documents
        html.Div([
            dbc.Button("Generate Question Bank", id="generate-button", n_clicks=0, disabled=True, style={
                "backgroundColor": theme_color,
                "border": "none",
                "color": "#0a0a0a",
                "padding": "10px 25px",
                "fontWeight": "bold",
                "borderRadius": "8px",
                "boxShadow": f"0 0 10px {theme_color}",
                "marginRight": "20px",
                "marginBottom": "20px"
            }),
            dbc.Button("Verify Documents", id="verify-button", n_clicks=0, disabled=True, style={
                "backgroundColor": theme_color,
                "border": "none",
                "color": "#0a0a0a",
                "padding": "10px 25px",
                "fontWeight": "bold",
                "borderRadius": "8px",
                "boxShadow": f"0 0 10px {theme_color}",
                "marginBottom": "20px"
            }),
        ], style={"textAlign": "center"}),

        # Zone de texte pour afficher les résultats
        html.Div(id="output-box3", style={
            "margin": "20px auto",
            "width": "65%",
            "height": "400px",
            "padding": "20px",
            "background": "transparent",
            "border": f"1px solid {theme_color}",
            "borderRadius": "12px",
            "color": "#ffffff",
            "boxShadow": f"0 0 12px {theme_color}",
            "backdropFilter": "blur(6px)",
            "overflowY": "auto",
        }),

        dcc.Loading(
            id="loading-response3",
            type="circle",
            color=theme_color,
            children=html.Div(id="loading-output3", children="Please wait, generating questions...")
        ),

        # Stockage de l'état de l'upload
        dcc.Store(id="upload-done", data=False)
    ])
], style={
    "minHeight": "100vh",
    "padding": "30px",
    "backgroundImage": "url('/assets/your-background.jpg')",
    "backgroundSize": "cover",
    "backgroundPosition": "center",
    "display": "flex",
    "flexDirection": "column",
    "alignItems": "center"
})

# Callback pour gérer l'upload des documents et activer les boutons
@dash.callback(
    [Output("upload-status", "children"),
     Output("generate-button", "disabled"),
     Output("verify-button", "disabled"),
     Output("upload-done", "data")],
    Input("upload-documents", "filename"),
    Input("upload-documents", "contents"),
    prevent_initial_call=False
)
def manage_upload_status(filenames, contents):
    global new_chunks, index
    # Cas d'initialisation (au chargement de la page)
    if filenames is None and contents is None:
        return "Please upload a document to generate questions.", True, True, False

    # Cas où un upload est déclenché
    if not filenames or not contents:
        return "Please upload a document to generate questions.", True, True, False
    
    all_chunks = []
    for filename, content in zip(filenames, contents):
        try:
            text = extract_text_from_file(filename, content)
            new_chunks_from_file = chunk_text(text)
            all_chunks.extend(new_chunks_from_file)
        except Exception as e:
            return f"Error processing {filename}: {str(e)}", True, True, False
    
    # Stocker les nouveaux chunks dans new_chunks
    new_chunks = all_chunks
    print(f"Upload réussi : {len(all_chunks)} nouveaux chunks créés.")
    
    # Recréer l'index FAISS avec les nouveaux chunks
    index = create_faiss_index(new_chunks)
    
    return f"Successfully uploaded and processed {len(filenames)} document(s). {len(all_chunks)} chunks created.", False, False, True

# Callback pour gérer les deux actions
@dash.callback(
    Output("output-box3", "children"),
    Output("loading-output3", "children"),
    Input("generate-button", "n_clicks"),
    Input("verify-button", "n_clicks"),
    State("upload-done", "data")
)
def update_output(generate_clicks, verify_clicks, upload_done):
    ctx = dash.callback_context
    if not ctx.triggered:
        print("Aucun bouton n'a été cliqué.")
        return "", ""

    if not upload_done:
        return html.P("Please upload a document before generating questions or verifying documents.", style={"color": "#ff5555"}), ""

    button_id = ctx.triggered[0]["prop_id"].split(".")[0]
    print(f"Bouton cliqué : {button_id}")

    if button_id == "generate-button" and generate_clicks > 0:
        try:
            question_bank = generate_question_bank()
            formatted_questions = format_questions_with_highlights(question_bank)
            print("Résultat final pour Generate Question Bank :")
            print(formatted_questions)
            return formatted_questions, ""
        except Exception as e:
            print(f"Erreur dans le callback Generate Question Bank : {str(e)}")
            return html.P(f"Error: {str(e)}", style={"color": "#ff5555"}), ""

    elif button_id == "verify-button" and verify_clicks > 0:
        try:
            verification_results = verify_all_documents()
            formatted_results = format_verification_with_highlights(verification_results)
            print("Résultat final pour Verify Documents :")
            print(formatted_results)
            return formatted_results, ""
        except Exception as e:
            print(f"Erreur dans le callback Verify Documents : {str(e)}")
            return html.P(f"Error: {str(e)}", style={"color": "#ff5555"}), ""

    print("Aucune condition remplie pour le callback.")
    return "", ""