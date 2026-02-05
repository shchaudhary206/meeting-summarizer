import streamlit as st
import os
import time
import json
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv

# 1. Setup & Auth
load_dotenv()

# Try to get keys from Streamlit Secrets (Cloud) or local .env (Localhost)
try:
    api_key = st.secrets["GOOGLE_API_KEY"]
    app_password = st.secrets["APP_PASSWORD"]
except:
    # Fallback for local testing if not using secrets.toml
    api_key = os.getenv("GOOGLE_API_KEY")
    app_password = "password" # Default local password

# Configure Gemini
if not api_key:
    st.error("Google API Key not found.")
    st.stop()

genai.configure(api_key=api_key)

# 2. Password Protection Logic
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

def check_password():
    if st.session_state.password_input == app_password:
        st.session_state.authenticated = True
        del st.session_state.password_input
    else:
        st.error("😕 Wrong password")

if not st.session_state.authenticated:
    st.title("🔒 Login Required")
    st.write("Please enter the password to access the Meeting Summarizer.")
    st.text_input("Enter Password:", type="password", key="password_input", on_change=check_password)
    st.stop() # Stops the app here until logged in

# 3. Main App (Runs only after login)
st.title("🎙️ AI Meeting Summarizer")
st.write(f"Welcome! You are logged in.")

uploaded_file = st.file_uploader("Upload Audio (MP3)", type=["mp3"])

if uploaded_file is not None:
    if st.button("Generate Summary"):
        
        # Save temp file
        temp_filename = "temp_upload.mp3"
        with open(temp_filename, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        status_text = st.empty()
        status_text.text("Uploading file to Gemini...")

        try:
            myfile = genai.upload_file(temp_filename, mime_type="audio/mpeg")
            
            status_text.text("Processing audio...")
            while myfile.state.name == "PROCESSING":
                time.sleep(2)
                myfile = genai.get_file(myfile.name)

            status_text.text("Generating summary...")
            model = genai.GenerativeModel('gemini-1.5-flash')
            
            # Standard Prompt (No Speaker ID)
            prompt = """
            Listen to this meeting recording carefully.
            Create a JSON object with two keys:
            1. "summary": A concise paragraph summarizing the discussion.
            2. "action_items": A list of objects, where each object has an "owner" (who needs to do it) and a "task" (what they need to do).
            
            Example JSON format:
            {
              "summary": "The team discussed...",
              "action_items": [
                {"owner": "Marketing Team", "task": "Prepare Q3 deck"},
                {"owner": "John", "task": "Email the client"}
              ]
            }
            """
            
            response = model.generate_content([myfile, prompt])
            
            # Clean and Parse
            cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
            json_data = json.loads(cleaned_text)

            # --- Display Results ---
            st.success("Analysis Complete!")
            status_text.empty()

            st.header("📋 Summary")
            st.write(json_data.get("summary", "No summary available."))

            st.header("✅ Action Items")
            actions = json_data.get("action_items", [])
            
            for item in actions:
                if isinstance(item, dict):
                    st.markdown(f"- **{item.get('owner', 'Unknown')}**: {item.get('task')}")
                else:
                    st.markdown(f"- {item}")

            # --- Export to Excel ---
            excel_data = []
            excel_data.append({"Category": "Summary", "Owner": "All", "Task": json_data.get("summary")})
            
            for item in actions:
                if isinstance(item, dict):
                    excel_data.append({"Category": "Action Item", "Owner": item.get("owner"), "Task": item.get("task")})
                else:
                    excel_data.append({"Category": "Action Item", "Owner": "Unknown", "Task": item})
            
            df = pd.DataFrame(excel_data)
            output_excel_path = "meeting_report.xlsx"
            df.to_excel(output_excel_path, index=False)

            with open(output_excel_path, "rb") as file:
                st.download_button(
                    label="📥 Download Excel Report",
                    data=file,
                    file_name="meeting_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"An error occurred: {e}")
