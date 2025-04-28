import streamlit as st

# ==== Dummy users database (tu peux connecter à MongoDB après) ====
users_db = {
    "admin@example.com": "admin123",
    "user@example.com": "user123"
}

# ==== Login Page ====
def show_login_page():
    st.title("🔐 Login to ChaInvestor_Hub")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    login_button = st.button("Login")

    if login_button:
        if email in users_db and users_db[email] == password:
            st.success("✅ Logged in successfully!")
            st.session_state.user = email
            st.session_state.page = "home"
            st.rerun()
        else:
            st.error("❌ Invalid credentials. Try again.")

    st.markdown("Don't have an account yet? [Sign Up](?page=signup)")

# ==== Signup Page ====
def show_signup_page():
    st.title("📝 Create an Account - ChaInvestor_Hub")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    confirm_password = st.text_input("Confirm Password", type="password")
    signup_button = st.button("Sign Up")

    if signup_button:
        if password != confirm_password:
            st.error("❌ Passwords do not match.")
        elif email in users_db:
            st.error("❌ Email already registered.")
        else:
            users_db[email] = password
            st.success("✅ Account created! You can now login.")
            st.markdown("[Go to Login](?page=login)")
