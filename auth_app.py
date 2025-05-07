import streamlit as st
import pyrebase
import json

# Load Firebase config
with open("firebase_config.json") as f:
    firebase_config = json.load(f)

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()

# Session state keys
if "user" not in st.session_state:
    st.session_state.user = None
if "email" not in st.session_state:
    st.session_state.email = None

def login_ui():
    st.subheader("Login")
    email = st.text_input("Email")
    password = st.text_input("Password", type="password")
    if st.button("Login"):
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            st.success("Logged in successfully!")
            st.session_state.user = user
            st.session_state.email = email
            st.experimental_rerun()
        except Exception as e:
            st.error("Login failed. Please check your credentials.")

def signup_ui():
    st.subheader("Sign Up")
    email = st.text_input("Email", key="signup_email")
    password = st.text_input("Password", type="password", key="signup_password")
    confirm_password = st.text_input("Confirm Password", type="password", key="signup_confirm")

    if st.button("Create Account"):
        if password != confirm_password:
            st.error("Passwords do not match.")
            return
        try:
            user = auth.create_user_with_email_and_password(email, password)
            st.success("Account created! You can now log in.")
        except Exception as e:
            st.error("Signup failed. Email may already be registered.")

def main_app():
    st.title("🎉 Welcome to ThriveBot!")
    st.write(f"You're logged in as **{st.session_state.email}**.")

    if st.button("Log out"):
        st.session_state.user = None
        st.session_state.email = None
        st.experimental_rerun()

    # Your chatbot or dashboard can go here:
    st.write("✅ This is where your chatbot or health app logic goes.")

# Routing
def main():
    st.title("🧠 ThriveBot Auth")
    if st.session_state.user:
        main_app()
    else:
        tab1, tab2 = st.tabs(["Login", "Sign Up"])
        with tab1:
            login_ui()
        with tab2:
            signup_ui()

if __name__ == "__main__":
    main()
