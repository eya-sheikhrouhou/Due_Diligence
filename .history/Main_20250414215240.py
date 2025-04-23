import streamlit as st
from auth import show_login_page
from reponses import show_due_diligence_app

st.set_page_config(page_title="💬 Due Diligence AI", layout="wide")

if "user" not in st.session_state:
    st.session_state.user = None

if st.session_state.user:
    show_due_diligence_app()
else:
    show_login_page()
