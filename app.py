import streamlit as st
import os
import json
import fitz  # PyMuPDF
from dotenv import load_dotenv
import pyrebase
from openai import AzureOpenAI

# --- ENV + CONFIG ---
load_dotenv()

firebase_config = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
    "measurementId": os.getenv("FIREBASE_MEASUREMENT_ID"),
    "databaseURL": os.getenv("FIREBASE_DATABASE_URL", "https://dummy.firebaseio.com")
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

client = AzureOpenAI(
    api_key=os.getenv("AZURE_API_KEY"),
    api_version=os.getenv("AZURE_API_VERSION"),
    azure_endpoint=os.getenv("AZURE_ENDPOINT")
)

# --- PAGE CONFIG ---
st.set_page_config(page_title="T.H.R.I.V.E.", layout="centered")
st.markdown("<style>footer {visibility: hidden;}</style>", unsafe_allow_html=True)

# --- SESSION STATE ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "system", "content": "You are an expert health coach."}]
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""

# --- AUTH ---
def login_ui():
    st.markdown("## 🔐 Login or Register to Access T.H.R.I.V.E.")

    mode = st.radio("Choose mode", ["Login", "Register", "Forgot Password"], horizontal=True)

    email = st.text_input("Email", placeholder="you@example.com")

    if mode in ["Login", "Register"]:
        password = st.text_input("Password", type="password")

    if mode == "Register":
        confirm_pw = st.text_input("Confirm Password", type="password")

    if st.button(mode):
        if not email or (mode in ["Login", "Register"] and not password):
            st.warning("Please fill in all required fields.")
            return

        try:
            if mode == "Login":
                user = auth.sign_in_with_email_and_password(email, password)
                st.session_state.authenticated = True
                st.session_state.user = user
                st.success("✅ Login successful!")
                st.rerun()

            elif mode == "Register":
                if password != confirm_pw:
                    st.error("❌ Passwords do not match.")
                    return
                user = auth.create_user_with_email_and_password(email, password)
                st.session_state.authenticated = True
                st.session_state.user = user
                st.success("🎉 Account created and logged in!")
                st.rerun()

            elif mode == "Forgot Password":
                auth.send_password_reset_email(email)
                st.success(f"📧 Password reset email sent to `{email}`. Check your inbox.")

        except Exception as e:
            st.error(f"❌ {mode} failed. Error: {e}")



def logout():
    if st.sidebar.button("Logout"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()

# --- PDF UTIL ---
def extract_and_summarize_pdf(uploaded_file):
    extracted_text = ""
    with fitz.open(stream=uploaded_file.read(), filetype="pdf") as doc:
        for page in doc:
            extracted_text += page.get_text()

    if len(extracted_text) > 3000:
        st.info("Long document detected. Summarizing...")
        summary_prompt = (
            "Summarize the following health document in bullet points. Focus on key findings, metrics, and possible health issues.\n\n"
            + extracted_text
        )
        summary_response = client.chat.completions.create(
            model=os.getenv("AZURE_DEPLOYMENT_NAME"),
            messages=[
                {"role": "system", "content": "You are a helpful medical assistant."},
                {"role": "user", "content": summary_prompt}
            ],
            temperature=0.5,
            max_tokens=800
        )
        return summary_response.choices[0].message.content.strip()
    return extracted_text

# --- CHAT UI ---
def chat_interface():
    # Sidebar user info
    st.sidebar.markdown("### 👤 Logged in as")
    st.sidebar.success(st.session_state.user["email"])
    logout()

    st.title("T.H.R.I.V.E.")
    st.markdown("_Your AI health coach for root-cause health solutions._")

    st.markdown("---")
    st.markdown("### 📄 Upload Health Report (PDF)")
    uploaded_file = st.file_uploader("Optional: Upload a lab report or health summary", type=["pdf"])

    if uploaded_file:
        try:
            st.session_state.pdf_text = extract_and_summarize_pdf(uploaded_file)
            st.success("PDF processed. You may now ask questions about it.")
        except Exception as e:
            st.error(f"Failed to read PDF: {e}")

    st.markdown("---")
    st.markdown("### 🧠 Ask T.H.R.I.V.E. a Health Question")

    prompt = st.chat_input("Enter your question here...")
    if prompt:
        if len(st.session_state.chat_history) == 1:
            intro_prompt = (
                "You are a compassionate health coach specializing in root-cause solutions using functional medicine and traditional Chinese medicine. "
                f"Here is the user's health document: {st.session_state.pdf_text}\n\nUser question: {prompt}"
            )
            st.session_state.chat_history.append({"role": "user", "content": intro_prompt})
        else:
            st.session_state.chat_history.append({"role": "user", "content": prompt})

        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("T.H.R.I.V.E. is thinking..."):
            try:
                response = client.chat.completions.create(
                    model=os.getenv("AZURE_DEPLOYMENT_NAME"),
                    messages=st.session_state.chat_history,
                    temperature=0.6,
                    max_tokens=800
                )
                reply = response.choices[0].message.content.strip()
                st.session_state.chat_history.append({"role": "assistant", "content": reply})

                with st.chat_message("assistant"):
                    st.markdown(reply)
            except Exception as e:
                st.error(f"Chat error: {e}")

    # Chat history viewer
    with st.expander("🗂 Chat History", expanded=False):
        for msg in st.session_state.chat_history:
            if msg["role"] != "system":
                role = "🧍 You" if msg["role"] == "user" else "THRIVE"
                st.markdown(f"**{role}:** {msg['content']}")

# --- APP FLOW ---
if st.session_state.authenticated:
    chat_interface()
else:
    login_ui()
