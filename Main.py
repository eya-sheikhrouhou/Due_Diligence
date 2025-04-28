# ==== Imports ====
import streamlit as st
import streamlit.components.v1 as components
from auth import show_login_page, show_signup_page
from test import show_due_diligence_app


# ==== Streamlit Page Configuration ====
st.set_page_config(page_title="ChaInvestor Hub", layout="wide", initial_sidebar_state="collapsed")

# ==== Global Stylish CSS ====
st.markdown("""
<style>
html, body, .stApp {
    background: #ffffff;
    font-family: 'Poppins', sans-serif;
    color: #333;
    scroll-behavior: smooth;
}

/* Titres */
h1, h2, h3 {
    font-weight: 700;
    color: #D4AF37; /* Gold */
}

/* Navbar */
.navbar {
    background: white;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    padding: 15px 30px;
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 30px;
    position: sticky;
    top: 0;
    z-index: 999;
}
.navbar a {
    color: #D4AF37; /* Gold */
    text-decoration: none;
    font-weight: 600;
    font-size: 18px;
    padding: 10px 15px;
    border-radius: 50px;
    transition: all 0.3s ease;
}
.navbar a:hover {
    background-color: #D4AF37; /* Gold background on hover */
    color: white; /* Texte devient blanc */
}

/* Bouton Login */
.stButton > button {
    background-color: #D4AF37; /* Bleu pour Login */
    border: none;
    color: white;
    border-radius: 50px;
    padding: 0.7rem 1.5rem;
    font-size: 1.1rem;
    transition: 0.3s;
}
.stButton > button:hover {
    background-color: #084298; /* Bleu foncé pour hover */
}

/* Footer */
.footer {
    margin-top: 5rem;
    padding: 2rem;
    background: #D4AF37; /* Gold */
    color: white;
    text-align: center;
    border-radius: 12px 12px 0 0;
}

/* Fade In animation */
.fade-in {
    animation: fadeIn 2s ease-in-out;
}
@keyframes fadeIn {
    0% {opacity: 0;}
    100% {opacity: 1;}
}
</style>
""", unsafe_allow_html=True)







# ==== Navbar ====
import base64

def show_navbar():
    # Lire l'image du logo en base64
    with open("assets/images/ChaInvestor_Hub.png", "rb") as img_file:
        logo_base64 = base64.b64encode(img_file.read()).decode()

    if st.session_state.user is None:
        login_button = '<a href="?page=login" class="login-button">Login</a>'
    else:
        login_button = '<a href="?page=home" class="login-button">Dashboard</a>'

    navbar_html = f"""
    <div class="navbar">
        <div class="navbar-left">
            <img src="data:image/png;base64,{logo_base64}" alt="Logo" style="height:50px;">
        </div>
        <div class="navbar-center">
            <a href="?page=home">Home</a>
            <a href="?page=services">Services</a>
            <a href="?page=about">About</a>
            <a href="?page=contact">Contact</a>
        </div>
        <div class="navbar-right">
            {login_button}
        </div>
    </div>
    """

    st.markdown(navbar_html, unsafe_allow_html=True)




# ==== Footer ====
def show_footer():
    st.markdown("""
    <div class="footer">
        © ChaInvestor_Hub 2025 | All rights reserved
    </div>
    """, unsafe_allow_html=True)

# ==== Pages ====
def show_home():
    show_navbar()

    # Lire l'image en Base64
    with open("assets/images/bb.png", "rb") as img_file:
        img_base64 = base64.b64encode(img_file.read()).decode()

    st.markdown(f"""
    <div style="
        position: relative;
        width: 100%;
        height: 90vh;
        background-image: url('data:image/png;base64,{img_base64}');
        background-size: cover;
        background-position: center;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        text-align: center;
        color: #D4AF37;
        padding: 2rem;
    ">
        <h1 style="font-size: 3.5rem; font-weight: 900; text-shadow: 2px 2px 5px rgba(0,0,0,0.5);">
            Smart Insights for Your Trusted Decisions
        </h1>
        <p style="font-size: 1.5rem; color: white; margin-top: 1rem; max-width: 700px; text-shadow: 1px 1px 4px rgba(0,0,0,0.5);">
            Empowering investors, startups, and enterprises to make faster, smarter, and more informed decisions.
        </p>
        <a href="?page=services" style="
            margin-top: 2rem;
            background-color: #D4AF37;
            color: white;
            padding: 15px 40px;
            font-size: 1.2rem;
            font-weight: bold;
            border-radius: 50px;
            text-decoration: none;
            box-shadow: 2px 2px 8px rgba(0,0,0,0.3);
            transition: background-color 0.3s ease;
        " onmouseover="this.style.backgroundColor='#b9922f'" onmouseout="this.style.backgroundColor='#D4AF37'">
              Explore Our Services
        </a>
    </div>
    """, unsafe_allow_html=True)

    show_footer()
    
def show_services():
    show_navbar()
    st.markdown("""
    <div class="fade-in" style="padding: 3rem 2rem; text-align: center;">
        <h2 style="color: #D4AF37;">Our Services</h2>
        <p style="font-size: 1.1rem; color: #555;">Tailored solutions for your due diligence needs</p>
    </div>
    """, unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown(service_card("Document Review", "Automated analysis of documents to speed up risk identification."), unsafe_allow_html=True)
    with col2:
        st.markdown(service_card("Background Check", "Smart background verification on entities and founders."), unsafe_allow_html=True)
    with col3:
        st.markdown(service_card("Risk Analysis", "AI-powered red flag detection for smarter decision making."), unsafe_allow_html=True)
    show_footer()

def show_about():
    show_navbar()
    st.markdown("""
    <div class="fade-in" style="padding: 4rem 2rem; background: white; text-align: center;">
        <h2 style="color: #D4AF37;">About Us</h2>
        <p style="font-size: 1.2rem; color: #555;">We are a team of experts in AI, finance, and compliance. Our mission is to empower businesses to make smarter decisions by providing innovative due diligence solutions.</p>
    </div>
    """, unsafe_allow_html=True)
    show_footer()

def show_contact():
    show_navbar()
    st.markdown("""
    <div class="fade-in" style="padding: 4rem 2rem; background: white; text-align: center;">
        <h2 style="color: #D4AF37;">Contact Us</h2>
        <p style="font-size: 1.1rem; color: #555;">We would love to hear from you.</p>
        <p>Email: <a href="mailto:contact@chainvestorhub.com" style="color: #D4AF37;">contact@chainvestorhub.com</a></p>
        <p>Phone: +1 (800) 123-4567</p>
    </div>
    """, unsafe_allow_html=True)
    show_footer()

# ==== Helper Service Card ====
def service_card(title, description):
    return f"""
    <div style="background:white; padding:2rem; border-radius:12px; box-shadow:0 2px 8px rgba(0,0,0,0.1); text-align:center;">
        <h3 style="color:#D4AF37;">{title}</h3>
        <p style="color:#555;">{description}</p>
    </div>
    """

# ==== Routing Logic ====
def get_page_from_url():
    query_params = st.query_params
    if "page" in query_params:
        return query_params["page"]
    return "home"

# ==== Main ====
page = get_page_from_url()


# Important pour synchroniser la navbar avec la session
if page in ["home", "services", "about", "contact", "login", "signup"]:
    st.session_state.page = page


if "user" not in st.session_state:
    st.session_state.user = None
if "page" not in st.session_state:
    st.session_state.page = "home"

if st.session_state.user:
    show_due_diligence_app()
elif st.session_state.page == "login":
    show_login_page()
elif st.session_state.page == "signup":
    show_signup_page()#
else:
    if page == "home":
        show_home()
    elif page == "services":
        show_services()
    elif page == "about":
        show_about()
    elif page == "contact":
        show_contact()
    else:
        show_home()
