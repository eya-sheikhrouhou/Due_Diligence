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

if "verification_step" not in st.session_state:
    st.session_state.verification_step = "request_email"  # pour le reset mot de passe    

# Page principale
if st.session_state.user:
    show_due_diligence_app()
elif st.session_state.page == "login":
    show_login_page()
elif st.session_state.page == "signup":
    show_signup_page()
elif st.session_state.page == "reset":
    from auth import show_reset_password_page
    show_reset_password_page()
else:
    import streamlit as st
    import streamlit.components.v1 as components



    # Function to get the current page based on URL parameters
    def get_page_from_url():
        query_params = st.query_params
        if "page" in query_params:
            return query_params["page"]
        return "home"  # Default page

    # Horizontal Navbar with clickable links
    st.markdown("""
        <style>
            .navbar {
                background-color: #1a1a1a;
                overflow: hidden;
                display: flex;
                justify-content: center;
                position: sticky;
                top: 0;
                z-index: 100;
            }
            .navbar a {
                float: left;
                display: block;
                color: #f1f1f1;
                text-align: center;
                padding: 14px 20px;
                text-decoration: none;
                font-size: 17px;
            }
            .navbar a:hover {
                background-color: #ddd;
                color: black;
            }
            .navbar a.active {
                background-color: #06f;
                color: white;
            }
        </style>
        <div class="navbar">
            <a href="?page=home" class="navbar-link">Home</a>
            <a href="?page=about" class="navbar-link">About</a>
            <a href="?page=services" class="navbar-link">Services</a>
            <a href="?page=contact" class="navbar-link">Contact</a>
        </div>
    """, unsafe_allow_html=True)

    # Get current page based on the URL query parameter
    page = get_page_from_url()

    # Content based on the selected page
    if page == "home":
        # Hero section
        st.markdown("""
            <div style="padding: 4rem 2rem; background: linear-gradient(to right, #1a1a1a, #0f0f0f); text-align: center; border-radius: 15px;">
                <h1 style="color: white; font-size: 3rem; font-weight: bold;">Smart Insights.<br>For Your Trusted Decisions</h1>
                <p style="color: #ccc; font-size: 1.3rem; max-width: 800px; margin: auto;">
                    Streamlined due diligence to empower investors, startups, and enterprises to make faster, smarter, and more informed decisions.
                </p>
            </div>
        """, unsafe_allow_html=True)

        # Create two columns for 'Why We Do This' and 'Helping You Grow In Every Stage'
        col1, col2 = st.columns(2)

        with col1:
            st.subheader("Why We Do This")
            st.markdown("""
                In today's fast-paced business environment, reliable due diligence is more essential than ever. 
                Our platform simplifies the process of evaluating businesses, investments, or partnerships 
                by automating document review, background checks, and financial validation.
            """)

        with col2:
            st.subheader("Helping You Grow In Every Stage")
            st.markdown("""
                Whether you're a venture capitalist, M&A advisor, or a startup founder, 
                we provide the tools to conduct thorough due diligence at every step — 
                from early-stage screening to final deal closing. Make faster, smarter decisions with confidence.
            """)

        # Value Proposition Section
        st.markdown("""
            <div style="padding: 3rem 2rem; background: #f4f4f4; border-radius: 15px; text-align: center;">
                <h2 style="color: #333; font-size: 2.5rem; font-weight: bold;">Analyze, Verify & Decide Confidently With Our Due Diligence Platform</h2>
                <p style="font-size: 1.2rem; color: #555; max-width: 800px; margin: auto;">
                    We've supported hundreds of companies in navigating risk and opportunity. 
                    With customizable workflows, smart alerts, and a secure data room, 
                    our platform is designed to streamline even the most complex due diligence processes.
                </p>
            </div>
        """, unsafe_allow_html=True)

        # Animated stats section
        components.html("""
            <div style="display: flex; justify-content: center; gap: 50px; margin-top: 4rem;">
                <div style="background-color:#111; padding:20px; border-radius:15px; text-align:center;">
                    <h1 id="count1" style="color:#06f;">0</h1>
                    <p style="color:white;">Entities Analyzed</p>
                </div>
                <div style="background-color:#111; padding:20px; border-radius:15px; text-align:center;">
                    <h1 id="count2" style="color:#06f;">0</h1>
                    <p style="color:white;">Deals Verified</p>
                </div>
                <div style="background-color:#111; padding:20px; border-radius:15px; text-align:center;">
                    <h1 id="count3" style="color:#06f;">0</h1>
                    <p style="color:white;">Total Value Screened ($)</p>
                </div>
            </div>

            <script>
                function animate(id, target, duration) {
                    const element = document.getElementById(id);
                    let count = 0;
                    const increment = target / (duration / 10);
                    const interval = setInterval(() => {
                        count += increment;
                        if (count >= target) {
                            count = target;
                            clearInterval(interval);
                        }
                        element.innerText = Math.floor(count).toLocaleString();
                    }, 10);
                }

                animate('count1', 1280, 2000);
                animate('count2', 347, 2000);
                animate('count3', 1500000000, 2000);
            </script>
        """, height=250)
        st.markdown("""
            <div style="padding: 4rem 2rem; background: linear-gradient(to right, #1a1a1a, #0f0f0f); text-align: center; border-radius: 15px; margin-top: 5rem;">
                <h1 style="color: white; font-size: 3rem; font-weight: bold;">Discover rare digital art<br>and collect NFTs</h1>
                <p style="color: #ccc; font-size: 1.3rem; max-width: 800px; margin: auto; margin-top: 1rem;">
                    The NFTs is a one-trick pony that climbed the recent years. The growth of NFTs is tremendous,
                    and according to Pymnts.com, the total sales volume
                </p>
                <div style="margin-top: 2.5rem;">
                    <a href="#" style="text-decoration: none; background-color: #06f; color: white; padding: 15px 30px; border-radius: 25px; font-size: 1.1rem; margin-right: 20px;">Create</a>
                    <a href="#" style="text-decoration: none; background-color: #333; color: white; padding: 15px 30px; border-radius: 25px; font-size: 1.1rem;">Contact Us</a>
                </div>
            </div>
        """, unsafe_allow_html=True)
        st.markdown("""
                <div style="margin-top: 5rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                <h2 style="color: white; font-size: 2.5rem;">Tags</h2>
                <a href="#" style="color: #06f; text-decoration: none; font-weight: bold;">VIEW ALL →</a>
                </div>
        
            <div style="display: flex; gap: 30px; flex-wrap: wrap; margin-top: 2rem;">
            <div style="background-color: #111; padding: 1rem; border-radius: 12px; width: 250px;">
                <p style="color: #06f; font-weight: bold; margin-top: 0.5rem;">DEVELOPMENT</p>
                <p style="color: #aaa; font-size: 0.9rem;">🕒 2 hour read</p>
                <h4 style="color: white; font-size: 1.1rem; margin-top: 0.5rem;">The services provide for design</h4>
            </div>

            <div style="background-color: #111; padding: 1rem; border-radius: 12px; width: 250px;">
                <p style="color: #06f; font-weight: bold; margin-top: 0.5rem;">DESIGN</p>
                <p style="color: #aaa; font-size: 0.9rem;">🕒 5 min read</p>
                <h4 style="color: white; font-size: 1.1rem; margin-top: 0.5rem;">More important feature for designer</h4>
            </div>

            <div style="background-color: #111; padding: 1rem; border-radius: 12px; width: 250px;">
                <p style="color: #06f; font-weight: bold; margin-top: 0.5rem;">MARKETING</p>
                <p style="color: #aaa; font-size: 0.9rem;">🕒 10 min read</p>
                <h4 style="color: white; font-size: 1.1rem; margin-top: 0.5rem;">Invalid purpose classes & motivation.</h4>
            </div>

            <div style="background-color: #111; padding: 1rem; border-radius: 12px; width: 250px;">
                <p style="color: #06f; font-weight: bold; margin-top: 0.5rem;">NFT'S</p>
                <p style="color: #aaa; font-size: 0.9rem;">🕒 1 min read</p>
                <h4 style="color: white; font-size: 1.1rem; margin-top: 0.5rem;">Canada is a great fact for NFT's</h4>
                </div>
            </div>
                </div>
            """, unsafe_allow_html=True)

        


        # Call to Action Section
        st.markdown("""
            <div style="padding: 3rem 2rem; background: #06f; color: white; text-align: center; border-radius: 15px; margin-top: 5rem;">
                <h2 style="font-size: 2.5rem; font-weight: bold;">Ready To Make Smarter Decisions?</h2>
                <p style="font-size: 1.2rem;">Join hundreds of businesses making confident decisions using our advanced due diligence platform. Start today!</p>
                <a href="#" style="text-decoration: none; background-color: #fff; color: #06f; padding: 15px 30px; border-radius: 25px; font-size: 1.1rem;">Get Started</a>
            </div>
        """, unsafe_allow_html=True)

        


    elif page == "about":
        st.markdown("""
            <div style="padding: 4rem 2rem; background: #f4f4f4; border-radius: 15px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1); text-align: center;">
                <h2 style="color: #333; font-size: 2.5rem; font-weight: bold;">About Us</h2>
                <p style="font-size: 1.2rem; color: #555; max-width: 800px; margin: auto;">
                    We are a team of passionate professionals dedicated to transforming the due diligence process.
                    Our platform combines cutting-edge technology, AI, and decades of experience to help investors,
                    startups, and enterprises make more informed decisions, faster.
                </p>
                <div style="display: flex; justify-content: space-around; flex-wrap: wrap; margin-top: 3rem;">
                    <div style="width: 250px; padding: 2rem; background: #fff; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); margin: 10px;">
                        <h3 style="color: #06f; font-size: 1.8rem; font-weight: bold;">Our Mission</h3>
                        <p style="font-size: 1.1rem; color: #777;">
                            Our mission is to simplify the due diligence process for everyone. We believe in empowering
                            our clients to make informed, confident decisions by automating key processes and offering
                            real-time insights.
                        </p>
                    </div>
                    <div style="width: 250px; padding: 2rem; background: #fff; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); margin: 10px;">
                        <h3 style="color: #06f; font-size: 1.8rem; font-weight: bold;">Our Vision</h3>
                        <p style="font-size: 1.1rem; color: #777;">
                            We aim to revolutionize due diligence by combining innovation, data security, and AI-driven
                            analytics to offer unmatched accuracy and speed in the decision-making process.
                        </p>
                    </div>
                    <div style="width: 250px; padding: 2rem; background: #fff; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1); margin: 10px;">
                        <h3 style="color: #06f; font-size: 1.8rem; font-weight: bold;">Our Values</h3>
                        <ul style="font-size: 1.1rem; color: #777; list-style-type: none; padding-left: 0;">
                            <li><i style="color: #06f; font-size: 1.2rem;">✔</i> Integrity</li>
                            <li><i style="color: #06f; font-size: 1.2rem;">✔</i> Innovation</li>
                            <li><i style="color: #06f; font-size: 1.2rem;">✔</i> Security</li>
                            <li><i style="color: #06f; font-size: 1.2rem;">✔</i> Efficiency</li>
                        </ul>
                    </div>
                </div>
            </div>

            <div style="background: #06f; color: white; padding: 3rem 2rem; text-align: center; margin-top: 5rem; border-radius: 15px;">
                <h2 style="font-size: 2.5rem;">Meet The Team</h2>
                <p style="font-size: 1.1rem;">Our team of experienced professionals is dedicated to delivering top-notch service and cutting-edge solutions to our clients. Together, we bring decades of expertise to the table, ensuring that every decision made is informed, accurate, and secure.</p>
                <div style="display: flex; justify-content: center; gap: 30px; margin-top: 2rem;">
                    <div style="width: 200px; text-align: center;">
                        <img src="https://via.placeholder.com/150" style="width: 150px; height: 150px; border-radius: 50%; margin-bottom: 1rem;" alt="Team Member">
                        <h3>John Doe</h3>
                        <p>CEO & Founder</p>
                    </div>
                    <div style="width: 200px; text-align: center;">
                        <img src="https://via.placeholder.com/150" style="width: 150px; height: 150px; border-radius: 50%; margin-bottom: 1rem;" alt="Team Member">
                        <h3>Jane Smith</h3>
                        <p>COO & Operations Lead</p>
                    </div>
                    <div style="width: 200px; text-align: center;">
                        <img src="https://via.placeholder.com/150" style="width: 150px; height: 150px; border-radius: 50%; margin-bottom: 1rem;" alt="Team Member">
                        <h3>Robert Brown</h3>
                        <p>CTO & Technical Lead</p>
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        


    elif page == "services":
        st.markdown("""
            <div style="padding: 4rem 2rem; background: #f4f4f4; border-radius: 15px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                <h2 style="color: #333;">Our Services</h2>
                <ul style="font-size: 1.1rem; color: #555;">
                    <li>AI-powered Document Review</li>
                    <li>Real-time Risk Analysis</li>
                    <li>Background Checks & Financial Validation</li>
                    <li>Customizable Workflows for Due Diligence</li>
                    <li>Secure Data Rooms for Sensitive Information</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

    elif page == "contact":
        st.markdown("""
            <div style="padding: 4rem 2rem; background: #f4f4f4; border-radius: 15px; box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);">
                <h2 style="color: #333;">Contact Us</h2>
                <p style="font-size: 1.1rem; color: #555;">
                    For inquiries, feedback, or partnership opportunities, please reach out to us through the following methods:
                </p>
                <ul style="font-size: 1.1rem; color: #555;">
                    <li>Email: <a href="mailto:info@duediligenceplatform.com" style="color: #06f;">info@duediligenceplatform.com</a></li>
                    <li>Phone: +1 (800) 123-4567</li>
                    <li>Address: 123 Business Avenue, Suite 456, New York, NY 10001</li>
                </ul>
            </div>
        """, unsafe_allow_html=True)

         # ✅ Modern centered buttons using Streamlit layout + session_state logic
    st.markdown("""
        <style>
            div.stButton > button {
                background-color: #111111;
                color: white;
                border: 1px solid #444;
                padding: 0.8rem 1.8rem;
                border-radius: 10px;
                font-size: 1rem;
                font-weight: 500;
                transition: all 0.3s ease;
                width: 100%;
            }
            div.stButton > button:hover {
                background-color: #06f;
                color: white;
                border-color: #06f;
            }
        </style>
    """, unsafe_allow_html=True)

    spacer1, col_connexion, spacer2, col_signup, spacer3, col_reset = st.columns([1, 2, 0.5, 2, 0.5, 2])

    with col_connexion:
        if st.button("🔐 Connexion"):
            st.session_state.page = "login"
            st.rerun()

    with col_signup:
        if st.button("📝 Créer un compte"):
            st.session_state.page = "signup"
            st.rerun()
    with col_reset:
        if st.button("🔁 Mot de passe oublié"):
            st.session_state.page = "reset"
            st.rerun()        
   


    # # Boutons centrés
    # col1, col2, col3 = st.columns([1, 2, 1])
    # with col2:
    #     if st.button("🔐 Connexion"):
    #         st.session_state.page = "login"
    #         st.rerun()
    #     if st.button("📝 Créer un compte"):
    #         st.session_state.page = "signup"
    #         st.rerun()
