import streamlit as st
import os
import json
import fitz  # PyMuPDF
from dotenv import load_dotenv
import pyrebase
from openai import AzureOpenAI
import pyodbc
from datetime import datetime
import uuid

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

# SQL Connection String
def get_sql_connection():
    conn_string = (
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={os.getenv('SQL_SERVER')};"
        f"DATABASE={os.getenv('SQL_DATABASE')};"
        f"UID={os.getenv('SQL_USERNAME')};"
        f"PWD={os.getenv('SQL_PASSWORD')};"
        f"Encrypt=yes;TrustServerCertificate=no;"
    )
    return pyodbc.connect(conn_string)

# --- PAGE CONFIG ---
st.set_page_config(page_title="T.H.R.I.V.E.", layout="centered")
st.markdown("<style>footer {visibility: hidden;}</style>", unsafe_allow_html=True)

# --- SESSION STATE ---
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False
if "user" not in st.session_state:
    st.session_state.user = None
if "chat_history" not in st.session_state:
    st.session_state.chat_history = [{"role": "system", "content": """You are T.H.R.I.V.E., a compassionate AI health coach specializing in root-cause health solutions using functional medicine and Traditional Chinese Medicine.

YOUR EXPERTISE:
- Functional medicine lab interpretation (bloodwork, hormones, nutrients, gut microbiome, biotoxins, etc.)
- TCM pattern diagnosis (qi stagnation, blood deficiency, dampness, heat, cold, etc.)
- Nutrition and lifestyle interventions
- Mind-body connection and stress management
- Proactive health optimization
- Supportive supplements and herbal medicine
                                      
YOUR APPROACH:
- Always seek root causes, not just symptom relief
- Provide evidence-based recommendations when possible
- Integrate Eastern and Western perspectives
- Empower users with education and actionable steps
- Use clear, accessible language
- Recommend specific dietary, lifestyle, and mind-body practices
- Suggest supplements/herbs only as adjuncts, not primary treatments
- Suggest lab tests when needed for deeper insights 

IMPORTANT BOUNDARIES:
- Never diagnose medical conditions
- Don't recommend specific medications or dosages
- Always suggest consulting healthcare providers for serious concerns
- Focus on natural preventive health and optimization

When reviewing health documents, highlight:
1. Biomarkers outside optimal ranges (not just "normal")
2. Patterns indicating systemic imbalances
3. Specific nutritional or lifestyle interventions
4. TCM perspectives on symptoms/patterns
5. Suggest specific supplements, herbs and TCM formulas, or lab tests when relevant

Respond with warmth, clarity, and practical guidance."""
}]
if "pdf_text" not in st.session_state:
    st.session_state.pdf_text = ""
if "user_profile" not in st.session_state:
    st.session_state.user_profile = None
if "current_entry_id" not in st.session_state:
    st.session_state.current_entry_id = None

# --- DATABASE FUNCTIONS ---
def get_or_create_user_profile(user_email):
    """Get existing profile or create new one"""
    try:
        conn = get_sql_connection()
        cursor = conn.cursor()
        
        # Check if profile exists
        cursor.execute(
            "SELECT TOP 1 user_id, name, age, sex, health_goals, symptoms, habits FROM UserProfile WHERE user_id = ?",
            (user_email,)
        )
        row = cursor.fetchone()
        
        if row:
            profile = {
                "user_id": row[0],
                "name": row[1],
                "age": row[2],
                "sex": row[3],
                "health_goals": row[4],
                "symptoms": row[5],
                "habits": row[6]
            }
        else:
            # Create new profile
            profile = {
                "user_id": user_email,
                "name": None,
                "age": None,
                "sex": None,
                "health_goals": None,
                "symptoms": None,
                "habits": None
            }
        
        conn.close()
        return profile
    except Exception as e:
        st.error(f"Database error: {e}")
        return None

def save_chat_entry(user_email, user_message, assistant_response, entry_id):
    """Save each chat interaction to database"""
    try:
        conn = get_sql_connection()
        cursor = conn.cursor()
        
        timestamp = datetime.now()
        
        # Extract profile info from session if available
        profile = st.session_state.user_profile or {}
        
        # Convert recommendations to JSON format to satisfy CHECK constraint
        recommendations_json = json.dumps({"response": assistant_response[:4000]})
        
        cursor.execute("""
            INSERT INTO UserHealthData 
            (user_id, entry_id, timestamp, age, sex, symptoms, habits, health_goals, recommendations, notes, name)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            user_email,
            entry_id,
            timestamp,
            profile.get('age'),
            profile.get('sex'),
            profile.get('symptoms'),
            profile.get('habits'),
            profile.get('health_goals'),
            recommendations_json,  # Now in JSON format
            user_message[:4000],
            profile.get('name')
        ))
        
        conn.commit()
        conn.close()
    except Exception as e:
        st.error(f"Failed to save chat: {e}")

def update_user_profile(user_email, name=None, age=None, sex=None, symptoms=None, habits=None, health_goals=None):
    """Update or create user profile"""
    try:
        conn = get_sql_connection()
        cursor = conn.cursor()
        
        timestamp = datetime.now()
        entry_id = str(uuid.uuid4())
        
        # Check if profile exists
        cursor.execute("SELECT COUNT(*) FROM UserProfile WHERE user_id = ?", (user_email,))
        exists = cursor.fetchone()[0] > 0
        
        if exists:
            cursor.execute("""
                UPDATE UserProfile 
                SET name = COALESCE(?, name),
                    age = COALESCE(?, age),
                    sex = COALESCE(?, sex),
                    symptoms = COALESCE(?, symptoms),
                    habits = COALESCE(?, habits),
                    health_goals = COALESCE(?, health_goals),
                    timestamp = ?
                WHERE user_id = ?
            """, (name, age, sex, symptoms, habits, health_goals, timestamp, user_email))
        else:
            cursor.execute("""
                INSERT INTO UserProfile 
                (user_id, entry_id, timestamp, name, age, sex, symptoms, habits, health_goals)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (user_email, entry_id, timestamp, name, age, sex, symptoms, habits, health_goals))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        st.error(f"Failed to update profile: {e}")
        return False

def load_recent_chat_history(user_email, limit=10):
    """Load recent chat history from database"""
    try:
        conn = get_sql_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT TOP (?) notes, recommendations, timestamp 
            FROM UserHealthData 
            WHERE user_id = ? 
            ORDER BY timestamp DESC
        """, (limit, user_email))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Convert to chat format (reverse to chronological order)
        history = []
        for row in reversed(rows):
            if row[0]:  # user message (notes)
                history.append({"role": "user", "content": row[0]})
            if row[1]:  # assistant message (recommendations)
                try:
                    # Parse JSON to get actual response
                    rec_data = json.loads(row[1])
                    response_text = rec_data.get('response', row[1])
                    history.append({"role": "assistant", "content": response_text})
                except:
                    # Fallback if not valid JSON
                    history.append({"role": "assistant", "content": row[1]})
        
        return history
    except Exception as e:
        st.error(f"Failed to load history: {e}")
        return []

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
                
                # Load user profile
                st.session_state.user_profile = get_or_create_user_profile(user['email'])
                
                st.success("✅ Login successful!")
                st.rerun()

            elif mode == "Register":
                if password != confirm_pw:
                    st.error("❌ Passwords do not match.")
                    return
                user = auth.create_user_with_email_and_password(email, password)
                st.session_state.authenticated = True
                st.session_state.user = user
                
                # Create user profile
                st.session_state.user_profile = get_or_create_user_profile(user['email'])
                
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
            max_tokens=3000
        )
        return summary_response.choices[0].message.content.strip()
    return extracted_text

# --- PROFILE SETUP ---
def profile_setup_ui():
    st.markdown("### 👤 Complete Your Health Profile")
    st.markdown("_Help T.H.R.I.V.E. provide personalized guidance_")
    
    profile = st.session_state.user_profile
    
    with st.form("profile_form"):
        name = st.text_input("Name (optional)", value=profile.get('name') or "")
        age = st.number_input("Age", min_value=1, max_value=120, value=profile.get('age') or 30)
        sex = st.selectbox("Sex", ["Prefer not to say", "Female", "Male", "Other"], 
                          index=0 if not profile.get('sex') else ["Prefer not to say", "Female", "Male", "Other"].index(profile.get('sex')))
        symptoms = st.text_area("Current symptoms or health concerns", value=profile.get('symptoms') or "", 
                               placeholder="e.g., fatigue, digestive issues, anxiety...")
        habits = st.text_area("Current habits (diet, exercise, sleep, etc.)", value=profile.get('habits') or "",
                             placeholder="e.g., vegetarian diet, yoga 3x/week, 6 hours sleep...")
        health_goals = st.text_area("Health goals", value=profile.get('health_goals') or "",
                                   placeholder="e.g., improve energy, reduce inflammation, better sleep...")
        
        submitted = st.form_submit_button("Save Profile")
        
        if submitted:
            success = update_user_profile(
                st.session_state.user['email'],
                name=name if name else None,
                age=age,
                sex=sex if sex != "Prefer not to say" else None,
                symptoms=symptoms if symptoms else None,
                habits=habits if habits else None,
                health_goals=health_goals if health_goals else None
            )
            if success:
                st.session_state.user_profile = get_or_create_user_profile(st.session_state.user['email'])
                st.success("✅ Profile saved!")
                st.rerun()

# --- CHAT UI ---
def chat_interface():
    # Sidebar
    st.sidebar.markdown("### 👤 Logged in as")
    st.sidebar.success(st.session_state.user["email"])
    
    # Profile summary
    if st.session_state.user_profile:
        profile = st.session_state.user_profile
        if profile.get('name'):
            st.sidebar.markdown(f"**Name:** {profile['name']}")
        if profile.get('age'):
            st.sidebar.markdown(f"**Age:** {profile['age']}")
    
    if st.sidebar.button("📝 Edit Profile"):
        st.session_state.show_profile = True
        st.rerun()
    
    if st.sidebar.button("📜 Load Chat History"):
        history = load_recent_chat_history(st.session_state.user['email'])
        if history:
            # Keep system prompt, add loaded history
            st.session_state.chat_history = [st.session_state.chat_history[0]] + history
            st.success(f"Loaded {len(history)} previous messages")
            st.rerun()
    
    logout()

    # Show profile setup if needed
    if st.session_state.get('show_profile', False):
        profile_setup_ui()
        if st.button("← Back to Chat"):
            st.session_state.show_profile = False
            st.rerun()
        return

    st.title("T.H.R.I.V.E.")
    st.markdown("_Your AI health coach for root-cause health solutions._")

    st.markdown("---")
    st.markdown("### 📄 Upload Health Report (PDF)")
    uploaded_file = st.file_uploader("Optional: Upload a lab report or health summary", type=["pdf"])

    if uploaded_file:
        try:
            st.session_state.pdf_text = extract_and_summarize_pdf(uploaded_file)
            st.success("✅ PDF processed. You may now ask questions about it.")
        except Exception as e:
            st.error(f"Failed to read PDF: {e}")

    st.markdown("---")
    st.markdown("### 🧠 Ask T.H.R.I.V.E. a Health Question")

    prompt = st.chat_input("Enter your question here...")
    if prompt:
        # Generate entry ID for this conversation
        if not st.session_state.current_entry_id:
            st.session_state.current_entry_id = str(uuid.uuid4())
        
        # Build user message - include PDF context and profile on first message
        user_message = prompt
        if len(st.session_state.chat_history) == 1:
            context_parts = []
            if st.session_state.pdf_text:
                context_parts.append(f"Health document: {st.session_state.pdf_text}")
            if st.session_state.user_profile:
                profile = st.session_state.user_profile
                profile_text = f"User profile - Age: {profile.get('age')}, Sex: {profile.get('sex')}, Goals: {profile.get('health_goals')}, Symptoms: {profile.get('symptoms')}, Habits: {profile.get('habits')}"
                context_parts.append(profile_text)
            
            if context_parts:
                user_message = f"[CONTEXT: {' | '.join(context_parts)}]\n\nUser question: {prompt}"
        
        st.session_state.chat_history.append({"role": "user", "content": user_message})

        with st.chat_message("user"):
            st.markdown(prompt)  # Display clean prompt to user

        with st.spinner("T.H.R.I.V.E. is thinking..."):
            try:
                response = client.chat.completions.create(
                    model=os.getenv("AZURE_DEPLOYMENT_NAME"),
                    messages=st.session_state.chat_history,
                    temperature=0.7,
                    max_tokens=1200
                )
                reply = response.choices[0].message.content.strip()
                st.session_state.chat_history.append({"role": "assistant", "content": reply})

                with st.chat_message("assistant"):
                    st.markdown(reply)
                
                # Save to database
                save_chat_entry(
                    st.session_state.user['email'],
                    prompt,  # Save clean user message
                    reply,
                    st.session_state.current_entry_id
                )
            except Exception as e:
                st.error(f"Chat error: {e}")

    # Chat history viewer
    with st.expander("🗂 Chat History", expanded=False):
        for msg in st.session_state.chat_history:
            if msg["role"] != "system":
                role = "🧑 You" if msg["role"] == "user" else "🤖 THRIVE"
                # Clean up display - remove context wrapper
                content = msg['content']
                if content.startswith("[CONTEXT:"):
                    content = content.split("User question: ", 1)[-1]
                st.markdown(f"**{role}:** {content}")

# --- APP FLOW ---
if st.session_state.authenticated:
    chat_interface()
else:
    login_ui()