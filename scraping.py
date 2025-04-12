import requests
from bs4 import BeautifulSoup
import csv
import time
import psycopg2

# Liste des catégories disponibles sur Cryptwerk
categories = [
    "Accounts", "Adult", "Art", "Auto", "Beauty", "Books", "CBD products",
    "computer-hardware", "Clothing", "internet-shops", "Electronics", "food",
    "gaming", "GiftCards", "Gifts", "Growing", "Health", "Home, garden",
    "Household appliance", "hypermarkets", "Jewelrie", "Kids", "Marketplaces",
    "Mining shops", "Music", "Pet store", "Pharmacy", "Precious metals", "Smoking",
    "Software", "Souvenirs", "Sport stores", "Travel", "Wallet store", "NFT", "digital goods", "Collecting", "Hobbies"
]

# Génération dynamique des URLs
base_url = "https://cryptwerk.com/companies/"
URLS = {
    category: {
        "BTC & ETH": f"{base_url}{category.lower().replace(', ', '-').replace(' ', '-')}/?coins=6,1",
        "BTC": f"{base_url}{category.lower().replace(', ', '-').replace(' ', '-')}/btc/",
        "ETH": f"{base_url}{category.lower().replace(', ', '-').replace(' ', '-')}/eth/"
    }
    for category in categories
}

# Headers pour éviter d'être bloqué par le site
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

def get_page_content(url):
    """Télécharge le contenu HTML d'une page"""
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            return response.text
        else:
            print(f"❌ Erreur {response.status_code} en accédant à {url}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"⚠️ Erreur réseau : {e}")
        return None

def parse_companies(html, category, crypto_type):
    """Extrait les informations des entreprises selon la catégorie et le type de crypto"""
    soup = BeautifulSoup(html, "html.parser")
    companies = []

    for item in soup.find_all("div", class_="item"):
        name = item.find("div", class_="title")
        name = name.text.strip() if name else "N/A"

        rating = item.find("span", class_="rating-bg-5") or item.find("span", class_="rating-bg-4") or item.find("span", class_="rating-bg-3")
        rating = rating.text.strip() if rating else "N/A"

        reviews = item.find("small", class_="reviews-counter")
        reviews = reviews.text.strip() if reviews else "0 reviews"

        companies.append([name, rating, reviews, category, crypto_type])

    return companies

def save_to_database(companies):
    """Enregistre les données extraites dans une base de données PostgreSQL"""
    try:
        # Se connecter à la base de données PostgreSQL
        connection = psycopg2.connect(
            dbname='cryptwerk',  # Nom de la base de données
            user='postgres',  # Remplace par ton nom d'utilisateur PostgreSQL
            password='bibi19',  # Remplace par ton mot de passe PostgreSQL
            host='localhost',
            port='5432'
        )
        cursor = connection.cursor()

        # Créer la table si elle n'existe pas
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS companies (
            name TEXT,
            rating TEXT,
            reviews TEXT,
            category TEXT,
            crypto_type TEXT
        );
        """)
        
        # Insérer les données dans la table
        for company in companies:
            cursor.execute("""
            INSERT INTO companies (name, rating, reviews, category, crypto_type)
            VALUES (%s, %s, %s, %s, %s);
            """, company)

        connection.commit()
        print("✅ Données enregistrées dans la base de données.")
    except Exception as e:
        print(f"⚠️ Erreur lors de l'enregistrement dans la base de données : {e}")
    finally:
        cursor.close()
        connection.close()

def scrape_and_save():
    """Scrape toutes les catégories et enregistre dans la base de données PostgreSQL"""
    all_companies = []

    for category, urls in URLS.items():
        for crypto_type, url in urls.items():
            print(f"🔎 Scraping {category} avec {crypto_type}...")
            html_content = get_page_content(url)

            if html_content:
                companies = parse_companies(html_content, category, crypto_type)
                all_companies.extend(companies)

            time.sleep(1)  # Pause d'une seconde pour éviter un blocage IP

    # Enregistrement des données dans la base de données
    if all_companies:
        save_to_database(all_companies)
    else:
        print("⚠️ Aucune entreprise trouvée.")

# Lancer le scraping et l'enregistrement des données
scrape_and_save()
