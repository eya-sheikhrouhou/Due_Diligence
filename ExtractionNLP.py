import os
import re
import PyPDF2
import spacy
from transformers import pipeline
from transformers import AutoTokenizer

tokenizer = AutoTokenizer.from_pretrained("facebook/bart-large-cnn")

# Initialisation
nlp = spacy.load("en_core_web_sm")
summarizer = pipeline("summarization", model="facebook/bart-large-cnn")

new_pdf_files = [
    "108364 PLE_Digital Assets_Deck 290724.pdf",
    "1110830.1.0 Introduction to Digital Assets for Institutional Investors_FINAL_0.pdf",
    "cravath-bringing-blockchain-due-diligence-into-focus-102024_vb-002.pdf",
    "DASCPWhitePaper.pdf",
    "Digital_Assets_Legal_Regulation_and_Estimation_of_.pdf",
    "ey-token-due-diligence-a-structured-approach-to-evaluate-digital-asset-risk (1).pdf",
    "ey-token-due-diligence-a-structured-approach-to-evaluate-digital-asset-risk.pdf",
    "FATF-Booklet_VA.pdf",
    "FTI+Technology+-+Decentralized+Due+Diligence.pdf",
    "guide-to-regulation-on-cryptocurrency-and-digital-token.pdf",
    "guide-to-the-vetting-of-digital-asset-and-digital-asset-exchanges.pdf",
    "mpdf.pdf",
    "Operational-Due-Diligence-on-Digital-Assets.pdf",
    "SSRN-id4594467.pdf",
    "us-crypto-regulatory-whitepaper.pdf",
    "WEF_Digital_Assets_Regulation_2024.pdf"
]

# Dossiers
output_dir = "resumes"
clean_text_dir = "cleaned_texts"
os.makedirs(output_dir, exist_ok=True)
os.makedirs(clean_text_dir, exist_ok=True)


def extract_text_from_pdf(pdf_file):
    """Extrait le texte brut d’un fichier PDF"""
    try:
        with open(pdf_file, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            text = "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
            return text.strip()
    except Exception as e:
        print(f"❌ Erreur d'extraction pour {pdf_file}: {e}")
        return ""


def clean_text(text):
    """Nettoie et restructure le texte extrait d’un PDF"""
    # Nettoyages initiaux
    text = re.sub(r'\u00a0', ' ', text)  # espace insécable
    text = re.sub(r'\n+', '\n', text)
    text = re.sub(r'[ \t]{2,}', ' ', text)
    text = re.sub(r'\bPage \d+\b', '', text)
    text = re.sub(r'http\S+', '', text)
    text = re.sub(r'[^\x00-\x7F]+', ' ', text)

    # Correction des mots collés
    text = re.sub(r'(?<=[a-z])(?=[A-Z])', '. ', text)  # mots collés : financialCrime → financial. Crime
    text = re.sub(r'(?<=\d)(?=[A-Z])', '. ', text)
    text = re.sub(r'(?<=[a-z])(?=\d)', ' ', text)

    # Segmentation NLP (phrases > 30 caractères)
    doc = nlp(text)
    sentences = [sent.text.strip() for sent in doc.sents if len(sent.text.strip()) > 30]

    return "\n".join(sentences)


def summarize_text(text):
    """Résumé avec BART avec tronquage propre via tokenizer"""
    try:
        # Tronquer proprement à 1024 tokens
        tokens = tokenizer.encode(text, truncation=True, max_length=1024, return_tensors="pt")
        decoded_input = tokenizer.decode(tokens[0], skip_special_tokens=True)

        # Vérifier la longueur de texte utile
        input_length = len(decoded_input.split())
        max_length = min(300, int(input_length * 0.8))
        min_length = max(50, int(input_length * 0.4))
        if min_length >= max_length:
            min_length = max_length - 10

        summary = summarizer(
            decoded_input,
            max_length=max_length,
            min_length=min_length,
            length_penalty=2.5,
            num_beams=6,
            do_sample=False
        )
        return summary[0]['summary_text']

    except Exception as e:
        print(f"❌ Erreur de résumé : {e}")
        return "Résumé non disponible en raison d'une erreur."
def process_pdfs():
    for pdf_file in new_pdf_files:
        print(f"\n📄 Traitement : {pdf_file}")

        # Extraction brute
        extracted = extract_text_from_pdf(pdf_file)
        if not extracted:
            continue

        print(f"🔹 Longueur brute : {len(extracted.split())} mots")

        # Nettoyage
        cleaned = clean_text(extracted)
        print(f"✅ Texte nettoyé : {len(cleaned.split())} mots, {cleaned.count('.')} phrases")

        # Sauvegarde texte nettoyé
        base = os.path.splitext(os.path.basename(pdf_file))[0]
        clean_path = os.path.join(clean_text_dir, f"cleaned_{base}.txt")
        with open(clean_path, "w", encoding="utf-8") as f:
            f.write(cleaned)

        # Résumé
        summary = summarize_text(cleaned)
        summary_path = os.path.join(output_dir, f"resume_{base}.txt")
        with open(summary_path, "w", encoding="utf-8") as f:
            f.write(summary)

        print(f"📝 Résumé sauvegardé : {summary_path}")


if __name__ == "__main__":
    process_pdfs()
