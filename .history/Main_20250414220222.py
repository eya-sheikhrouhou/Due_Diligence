import streamlit as st
from auth import show_login_page
from test import show_due_diligence_app

# --- Set config first ---
st.set_page_config(page_title="💬 Due Diligence AI", layout="wide")

# --- CSS for background + style ---
st.markdown("""
    <style>
        html, body {
            background: linear-gradient(to right, #f5f7fa, #c3cfe2);
        }
        .main-title {
            font-size: 3rem;
            font-weight: bold;
            text-align: center;
            margin-top: 2rem;
            color: #2E3B4E;
            animation: fadeIn 1s ease-in-out;
        }
        @keyframes fadeIn {
            from {opacity: 0;}
            to {opacity: 1;}
        }
        .credit {
            text-align: center;
            font-size: 0.9rem;
            margin-top: 2rem;
            color: gray;
        }
    </style>
""", unsafe_allow_html=True)

# --- Authenticated? ---
if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user:
    show_due_diligence_app()
else:
    st.markdown('<div class="main-title">💬 Due Diligence ChatGPT Assistant</div>', unsafe_allow_html=True)
    show_login_page()
