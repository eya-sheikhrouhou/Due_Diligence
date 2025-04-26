import streamlit as st
import sqlite3
import pandas as pd
import requests
import asyncio
import ollama

# --- PAGE CONFIG ---
st.set_page_config(page_title="Crypto-Friendly Companies", layout="wide")

# --- DARK MODE STYLING ---
st.markdown("""
    <style>
        body {
            background-color: #f5f5f5;
            color: black;
        }
        .stApp {
            background-color: #f5f5f5;
        }
        .trust-badge {
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-weight: bold;
            display: inline-block;
            color: white;
            margin-top: 1rem;
            margin-bottom: 1rem;
        }
        .green {
            background-color: #4CAF50;
        }
        .orange {
            background-color: #FF9800;
        }
        .red {
            background-color: #F44336;
        }
    </style>
""", unsafe_allow_html=True)

st.title("🧾 Crypto-Friendly Companies Explorer")

# --- DATABASE CONNECTION ---
DB_PATH = "/Users/yass/Desktop/cryptwerk.db"
conn = sqlite3.connect(DB_PATH)

# --- LOAD DATA ---
@st.cache_data
def load_data():
    query = "SELECT * FROM companies"
    df = pd.read_sql_query(query, conn)
    return df

df = load_data()

# --- FILTERS ---
cryptos = ["BTC", "ETH", "BTC & ETH"]
categories = sorted(df["category"].dropna().unique())

col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    selected_crypto = st.selectbox("Filter by accepted cryptocurrency:", ["All"] + cryptos)
with col2:
    selected_category = st.selectbox("Filter by business category:", ["All"] + categories)
with col3:
    keyword = st.text_input(
        "Search by company name or keyword:",
        value="",
        key="search_input"
    )

# --- FILTER FUNCTIONS ---
def filter_by_keyword(df, keyword):
    if keyword:
        keyword = keyword.strip().lower()
        return df[
            df["name"].str.lower().str.contains(keyword, na=False) |
            df["category"].str.lower().str.contains(keyword, na=False)
        ]
    return df

# --- APPLY FILTERS ---
filtered_df = df.copy()

if selected_crypto != "All":
    if selected_crypto == "BTC & ETH":
        filtered_df = filtered_df[
            filtered_df["crypto_type"].str.contains("BTC", na=False) &
            filtered_df["crypto_type"].str.contains("ETH", na=False)
        ]
    else:
        filtered_df = filtered_df[
            filtered_df["crypto_type"].str.contains(selected_crypto, na=False)
        ]

if selected_category != "All":
    filtered_df = filtered_df[filtered_df["category"] == selected_category]

filtered_df = filter_by_keyword(filtered_df, st.session_state.search_input)

# --- TRUST SCORE & AI DESCRIPTION HELPERS ---
async def check_web_presence(company_name):
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        query = f"https://www.google.com/search?q={company_name.replace(' ', '+')}"
        response = requests.get(query, headers=headers, timeout=5)
        return response.status_code == 200
    except:
        return False

async def compute_trust_score(row, progress):
    base = 50
    progress.progress(0.3, text="Checking reviews...")
    await asyncio.sleep(0.5)
    if row['reviews'] > 10:
        base += min(row['reviews'], 100) * 0.2
    progress.progress(0.5, text="Checking ratings...")
    await asyncio.sleep(0.5)
    if row['rating'] != 'N/A':
        try:
            base += float(row['rating']) * 5
        except:
            pass
    progress.progress(0.7, text="Checking accepted cryptos...")
    await asyncio.sleep(0.5)
    if 'BTC' in row['crypto_type'] and 'ETH' in row['crypto_type']:
        base += 10
    progress.progress(0.9, text="Checking web presence...")
    await asyncio.sleep(0.5)
    if await check_web_presence(row['name']):
        base += 5
    progress.progress(1.0, text="Done!")
    return round(min(base, 100), 1)

async def generate_company_description(name, category, crypto, reviews, rating):
    prompt = f"""
You are a crypto business analyst AI. Write a short, engaging, and informative paragraph that introduces this company:

Name: {name}
Category: {category}
Accepted Cryptocurrencies: {crypto}
Number of Reviews: {reviews}
Average Rating: {rating}

Focus on its reputation, innovation, and relevance in the crypto ecosystem.
"""
    try:
        response = ollama.chat(
            model="mistral",
            messages=[{"role": "user", "content": prompt}]
        )
        return response["message"]["content"]
    except Exception as e:
        return f"*Error generating description: {e}*"

def get_badge_color(score):
    if score >= 80:
        return "green"
    elif score >= 50:
        return "orange"
    else:
        return "red"

# --- DISPLAY COMPANIES ---
def display_companies():
    st.subheader(f"🔎 {len(filtered_df)} matching companies")

    if len(filtered_df) == 0:
        st.warning("No companies found matching your filters or search.")
    else:
        for idx, row in filtered_df.iterrows():
            company_name = row['name']
            google_link = f"https://www.google.com/search?q={company_name.replace(' ', '+')}"

            st.markdown(f"""
            <div style='padding: 1.5rem; margin-top: 1rem; border-radius: 1rem; border: 1px solid #333; box-shadow: 2px 2px 8px rgba(255,255,255,0.1);'>
                <h4 style="margin-bottom:0.5rem;">🏢 {company_name}</h4>
                <p style="margin:0;"><strong>Category:</strong> {row['category']} | <strong>Accepts:</strong> {row['crypto_type']}</p>
                <p style="margin-top:0.5rem;"><a href="{google_link}" target="_blank">🔗 Google Search</a></p>
            </div>
            """, unsafe_allow_html=True)

            with st.expander(f"🔍 See Trust Score & AI Summary for {company_name}"):
                col1, col2 = st.columns([1, 1])

                trust_button = col1.button(f"Calculate Trust Score", key=f"trust_{company_name}")
                summary_button = col2.button(f"Generate AI Summary", key=f"summary_{company_name}")

                if trust_button and f"trust_score_{company_name}" not in st.session_state:
                    progress = st.progress(0, text="Starting Trust Score...")
                    with st.spinner("⚡ Calculating Trust Score..."):
                        trust_score = asyncio.run(compute_trust_score(row, progress))
                        st.session_state[f"trust_score_{company_name}"] = trust_score
                        st.success("Trust Score Calculated!")

                if f"trust_score_{company_name}" in st.session_state:
                    trust_score = st.session_state[f"trust_score_{company_name}"]
                    color = get_badge_color(trust_score)
                    st.markdown(
                        f"<span class='trust-badge {color}'>Trust Score: {trust_score}/100</span>",
                        unsafe_allow_html=True
                    )

                st.divider()

                if summary_button:
                    with st.spinner("⚡ Generating AI Summary..."):
                        ai_summary = asyncio.run(generate_company_description(
                            name=company_name,
                            category=row["category"],
                            crypto=row["crypto_type"],
                            reviews=row["reviews"],
                            rating=row["rating"]
                        ))
                        st.session_state[f"ai_summary_{company_name}"] = ai_summary
                        st.success("AI Summary Generated!")

                if f"ai_summary_{company_name}" in st.session_state:
                    st.subheader("🧠 Company AI Summary")
                    st.markdown(st.session_state[f"ai_summary_{company_name}"])

# --- RUN ---
display_companies()
