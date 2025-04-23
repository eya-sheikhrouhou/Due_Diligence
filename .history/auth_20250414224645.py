import streamlit as st
import bcrypt
from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["due_diligence"]
users_col = db["users"]

def verify_password(password, hashed):
    return bcrypt.checkpw(password.encode(), hashed)

def show_signup_page():
    import streamlit as st
    from pymongo import MongoClient
    import bcrypt

    client = MongoClient("mongodb://localhost:27017/")
    db = client["due_diligence"]

    st.subheader("📝 Créer un compte")

    # Nouveaux champs
    first_name = st.text_input("Prénom")
    last_name = st.text_input("Nom de famille")
    email = st.text_input("Email")
    password = st.text_input("Mot de passe", type="password")
    confirm = st.text_input("Confirmer le mot de passe", type="password")

    if st.button("Créer mon compte"):
        if not first_name or not last_name:
            st.warning("⚠️ Veuillez remplir votre prénom et nom.")
        elif password != confirm:
            st.error("❌ Les mots de passe ne correspondent pas.")
        elif db["users"].find_one({"email": email}):
            st.warning("⚠️ Un compte existe déjà avec cet email.")
        else:
            hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
            db["users"].insert_one({
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": hashed_pw
            })
            st.success(f"✅ Compte créé avec succès, {first_name} {last_name} !")
            st.session_state.page = "login"
            st.rerun()

    # 👉 Boutons de navigation après le formulaire
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("🔑 Aller à la page de connexion"):
            st.session_state.page = "login"
            st.rerun()
    with col2:
        if st.button("🏠 Retour à l'accueil"):
            st.session_state.page = "home"
            st.rerun()

def show_login_page():
    st.markdown("""
        <style>
            .login-container {
                background-color: white;
                padding: 2.5rem;
                border-radius: 16px;
                max-width: 420px;
                margin: 5rem auto;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
            }
            .login-title {
                font-size: 1.8rem;
                font-weight: 700;
                text-align: center;
                color: #2E3B4E;
                margin-bottom: 1.5rem;
            }
            .stTextInput > div > div > input {
                font-size: 1rem;
                padding: 10px;
            }
            .stButton > button {
                font-size: 1rem;
                background-color: #2E86DE;
                color: white;
                border-radius: 8px;
                padding: 0.5rem 1rem;
                margin-bottom: 0.5rem;
            }
            .footer {
                text-align: center;
                margin-top: 1rem;
                color: gray;
                font-size: 0.9rem;
            }
        </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.markdown('<div class="login-title">🔐 Connexion sécurisée</div>', unsafe_allow_html=True)

    email = st.text_input("📧 Email", key="login_email")
    password = st.text_input("🔑 Mot de passe", type="password", key="login_password")

    if st.button("Se connecter"):
        user = users_col.find_one({"email": email})
        if user and verify_password(password, user["password"]):
            st.session_state.user = email
            st.success("✅ Connexion réussie")
            st.rerun()
        else:
            st.error("❌ Identifiants invalides")

    # 👉 Boutons en bas
    col1, col2 = st.columns([1, 1])
    with col1:
        if st.button("📝 Créer un compte"):
            st.session_state.page = "signup"
            st.rerun()
    with col2:
        if st.button("🏠 Retour à l'accueil"):
            st.session_state.page = "home"
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="footer">Pas encore de compte ? Cliquez sur "Créer un compte".</div>', unsafe_allow_html=True)
    st.stop()
