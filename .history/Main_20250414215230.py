from pymongo import MongoClient
import bcrypt

client = MongoClient("mongodb://localhost:27017/")
db = client["due_diligence"]

email = "admin@example.com"
password = "admin123"
hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())

db["users"].insert_one({
    "email": email,
    "password": hashed
})

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
