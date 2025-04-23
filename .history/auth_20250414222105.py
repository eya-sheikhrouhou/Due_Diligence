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
    email = st.text_input("Email")
    password = st.text_input("Mot de passe", type="password")
    confirm = st.text_input("Confirmer le mot de passe", type="password")

    if st.button("Créer mon compte"):
        if password != confirm:
            st.error("❌ Les mots de passe ne correspondent pas.")
        elif db["users"].find_one({"email": email}):
            st.warning("⚠️ Un compte existe déjà avec cet email.")
        else:
            hashed_pw = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
            db["users"].insert_one({"email": email, "password": hashed_pw})
            st.success("✅ Compte créé ! Connectez-vous maintenant.")

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

    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown('<div class="footer">Pas encore de compte ? Contactez l\'administrateur.</div>', unsafe_allow_html=True)
    st.stop()
