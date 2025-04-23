st.set_page_config("🔐 Auth Demo", layout="centered")
users_col = db["users"]

# 📌 Choix page
auth_mode = st.sidebar.radio("Menu", ["Login", "Signup", "Logout"])

# 🟢 Inscription
if auth_mode == "Signup":
    st.subheader("📝 Créer un compte")
    new_username = st.text_input("Nom d'utilisateur")
    new_email = st.text_input("Email")
    new_password = st.text_input("Mot de passe", type="password")
    if st.button("Créer un compte"):
        if users_col.find_one({"username": new_username}):
            st.error("🚫 Nom d'utilisateur déjà pris.")
        else:
            hashed_pw = hash_password(new_password)
            users_col.insert_one({
                "username": new_username,
                "email": new_email,
                "password": hashed_pw
            })
            st.success("✅ Compte créé avec succès. Vous pouvez maintenant vous connecter.")

# 🔒 Connexion
elif auth_mode == "Login":
    st.subheader("🔐 Connexion")
    username = st.text_input("Nom d'utilisateur")
    password = st.text_input("Mot de passe", type="password")
    if st.button("Se connecter"):
        user = users_col.find_one({"username": username})
        if user and check_password(password, user["password"]):
            st.session_state.authenticated = True
            st.session_state.username = username
            st.success(f"✅ Connecté en tant que {username}")
        else:
            st.error("❌ Identifiants incorrects.")

# 🚪 Déconnexion
elif auth_mode == "Logout":
    st.session_state.authenticated = False
    st.session_state.username = ""
    st.success("🔓 Déconnecté.")
    st.stop()

# 🔐 Vérifie l'état de session
if "authenticated" not in st.session_state or not st.session_state.authenticated:
    st.warning("Veuillez vous connecter pour accéder à l'application.")
    st.stop()
