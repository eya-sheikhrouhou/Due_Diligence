import streamlit as st
from auth import show_login_page, show_signup_page
from test import show_due_diligence_app  # 🔁 Rename test.py → reponses.py

# ✅ Doit être tout en haut
st.set_page_config(page_title="💬 Due Diligence AI", layout="wide")

# ✅ CSS stylé pour home
st.markdown("""
    <style>
        html, body {
            background: linear-gradient(to right, #f5f7fa, #c3cfe2);
        }
        .main-title {
            font-size: 3.5rem;
            font-weight: bold;
            text-align: center;
            margin-top: 3rem;
            color: #2E3B4E;
        }
        .subtitle {
            text-align: center;
            font-size: 1.2rem;
            color: #555;
            margin-bottom: 3rem;
        }
        .center-buttons {
            display: flex;
            justify-content: center;
            gap: 2rem;
            margin-top: 2rem;
        }
        .stButton > button {
            font-size: 1.1rem;
            padding: 0.7rem 2rem;
            border-radius: 8px;
        }
    </style>
""", unsafe_allow_html=True)

# Session utilisateur
if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "home"

# Page principale
if st.session_state.user:
    show_due_diligence_app()
elif st.session_state.page == "login":
    show_login_page()
elif st.session_state.page == "signup":
    show_signup_page()
else:


    # Boutons centrés
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔐 Connexion"):
            st.session_state.page = "login"
            st.rerun()
        if st.button("📝 Créer un compte"):
            st.session_state.page = "signup"
            st.rerun()
