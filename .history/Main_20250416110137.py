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
    import streamlit as st
    import streamlit.components.v1 as components

    st.set_page_config(page_title="VeriSure AI | Due Diligence", layout="wide")

    def get_page_from_url():
        query_params = st.query_params
        return query_params.get("page", "home")

    # Modern Navbar
    st.markdown("""
        <style>
            .navbar {
                background-color: #121212;
                display: flex;
                justify-content: center;
                padding: 1rem;
                border-bottom: 2px solid #06f;
            }
            .navbar a {
                color: #fff;
                margin: 0 15px;
                text-decoration: none;
                font-weight: 500;
                text-transform: uppercase;
                letter-spacing: 1px;
                font-size: 1rem;
                padding: 10px 15px;
                border-radius: 8px;
            }
            .navbar a:hover {
                background-color: #06f;
                color: #fff;
            }
        </style>
        <div class="navbar">
            <a href="?page=home">Home</a>
            <a href="?page=about">About</a>
            <a href="?page=services">Services</a>
            <a href="?page=contact">Contact</a>
        </div>
    """, unsafe_allow_html=True)

    page = get_page_from_url()

    if page == "home":
        st.markdown("""
            <div style="text-align:center; padding:4rem 2rem; background:linear-gradient(to right,#1a1a1a,#0f0f0f); border-radius:20px;">
                <h1 style="color:white; font-size:3rem;">AI-powered Due Diligence</h1>
                <p style="color:#ccc; font-size:1.2rem; max-width:700px; margin:auto;">Empower your team to analyze financial, legal, and strategic data efficiently and make confident decisions with our intelligent platform.</p>
            </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("Why VeriSure?")
            st.markdown("""
                - ⚙️ Automated document parsing and red flag detection
                - 🔎 Semantic search across uploaded documents
                - 📊 Real-time insights and alerts
            """)
        with col2:
            st.subheader("Use Cases")
            st.markdown("""
                - 💼 Startup funding evaluation
                - 🤝 M&A due diligence
                - 📂 Financial and compliance review
            """)

        st.markdown("---")

        components.html("""
            <div style='display:flex;justify-content:center;gap:30px;'>
                <div style='color:white;text-align:center;'>
                    <h2 id='val1' style='color:#06f;'>0</h2>
                    <p>Entities Analyzed</p>
                </div>
                <div style='color:white;text-align:center;'>
                    <h2 id='val2' style='color:#06f;'>0</h2>
                    <p>Deals Verified</p>
                </div>
                <div style='color:white;text-align:center;'>
                    <h2 id='val3' style='color:#06f;'>0</h2>
                    <p>Total Value Screened ($)</p>
                </div>
            </div>
            <script>
                function animate(id, target) {
                    let count = 0;
                    let el = document.getElementById(id);
                    let step = target / 100;
                    let interval = setInterval(() => {
                        count += step;
                        if (count >= target) {
                            el.innerText = target.toLocaleString();
                            clearInterval(interval);
                        } else {
                            el.innerText = Math.floor(count).toLocaleString();
                        }
                    }, 20);
                }
                animate('val1', 1500);
                animate('val2', 320);
                animate('val3', 1750000000);
            </script>
        """, height=150)

        st.markdown("""
            <div style="margin-top:3rem; text-align:center;">
                <a href="#" style="background:#06f; color:white; padding:0.8rem 2rem; border-radius:25px; font-size:1.1rem; text-decoration:none;">Try The Demo →</a>
            </div>
        """, unsafe_allow_html=True)

    elif page == "about":
        st.markdown("""
            <div style="background:#f9f9f9; padding:3rem; border-radius:15px; text-align:center;">
                <h2>About VeriSure AI</h2>
                <p>We're transforming how due diligence is done — with AI that helps you review faster, act smarter, and reduce risk.</p>
            </div>
        """, unsafe_allow_html=True)

    elif page == "services":
        st.markdown("""
            <div style="padding:3rem;">
                <h2 style="color:#06f;">Services</h2>
                <ul style="font-size:1.1rem;">
                    <li>🔍 AI-based PDF document parsing</li>
                    <li>📥 Upload portal with automatic text extraction</li>
                    <li>📑 Question generation and contextual Q&A</li>
                    <li>🧠 Semantic similarity search</li>
                    <li>📈 PowerPoint + CSV report generation</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

    elif page == "contact":
        st.markdown("""
            <div style="padding:3rem;">
                <h2 style="color:#06f;">Contact Us</h2>
                <p>Email: <a href="mailto:support@verisure.ai">support@verisure.ai</a></p>
                <p>Phone: +1 234 567 8901</p>
                <p>Location: 42 AI Street, Paris, France</p>
            </div>
        """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("🔐 Connexion"):
            st.session_state.page = "login"
            st.rerun()
        if st.button("📝 Créer un compte"):
            st.session_state.page = "signup"
            st.rerun()

    # Footer
    st.markdown("""
        <hr style="margin-top:3rem;">
        <p style="text-align:center; color:#999; font-size:0.9rem;">© 2025 VeriSure AI — All rights reserved.</p>
    """, unsafe_allow_html=True)