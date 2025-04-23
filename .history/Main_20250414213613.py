# ✅ Authentification complète avec MongoDB + bcrypt + Streamlit session
import os
import streamlit as st
import bcrypt
from pymongo import MongoClient

# 🔗 Connexion MongoDB
client = MongoClient("mongodb://localhost:27017/")
db = client["due_diligence"]
users_col = db["users"]

# 🔐 Fonctions utils

def hash_password(password):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt())

def check_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed)

# 🎨 Interface
st.set_page_config("🔐 Authentification", layout="centered")
st.title("🔐 Authentification utilisateur")

# 🧠 État de session
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "username" not in st.session_state:
    st.session_state.username = ""

# 🔄 Choix de l'action
option = st.sidebar.radio("Navigation", ["Login", "Signup", "Logout"])

# ✍️ Signup
if option == "Signup":
    st.subheader("📝 Créer un compte")
    new_username = st.text_input("Nom d'utilisateur")
    new_email = st.text_input("Email")
    new_password = st.text_input("Mot de passe", type="password")
    if st.button("Créer mon compte"):
        if users_col.find_one({"username": new_username}):
            st.error("🚫 Ce nom d'utilisateur existe déjà.")
        else:
            users_col.insert_one({
                "username": new_username,
                "email": new_email,
                "password": hash_password(new_password)
            })
            st.success("✅ Compte créé avec succès. Vous pouvez maintenant vous connecter.")

# 🔑 Login
elif option == "Login":
    st.subheader("🔐 Connexion")
    username = st.text_input("Nom d'utilisateur")
    password = st.text_input("Mot de passe", type="password")
    if st.button("Connexion"):
        user = users_col.find_one({"username": username})
        if user and check_password(password, user["password"]):
            st.session_state.authenticated = True
            st.session_state.username = username
            st.success(f"✅ Bienvenue {username} !")
        else:
            st.error("❌ Identifiants incorrects")

# 🚪 Déconnexion
elif option == "Logout":
    if st.session_state.authenticated:
        st.success(f"👋 {st.session_state.username} déconnecté.")
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.stop()

# 🧱 Protection de l'application principale
if not st.session_state.authenticated:
    st.warning("⚠️ Vous devez être connecté pour accéder à l'application.")
    st.stop()

# 🟢 Ici commence ton assistant complet de due diligence !
st.success(f"✅ Vous êtes connecté en tant que {st.session_state.username}")

# 👉 Intégrer ici ton assistant due diligence, par exemple :
# from due_diligence_app import run_app
# run_app(username=st.session_state.username)

st.write("➡️ Place ton code principal ici.")
io