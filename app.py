import streamlit as st
import os
import time
import json
import pandas as pd
import google.generativeai as genai
from dotenv import load_dotenv

# 1. Setup
load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")

# Check for API key immediately
if not api_key:
    st.error("Google API Key not found. Please check your .env file.")
    st.stop()

genai.configure(api_key=api_key)

# 2. App Layout
st.title("🎙️ AI Meeting Summarizer")
st.write("Upload an audio recording to extract a Summary and Action Items.")

# File Uploader Widget
uploaded_file = st.file_uploader("Upload Audio (MP3)", type=["mp3"])

if uploaded_file is not None:
    if st.button("Generate Summary"):
        
        # Save uploaded file temporarily so Gemini can read it
        temp_filename = "temp_upload.mp3"
        with open(temp_filename, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        status_text = st.empty()
        status_text.text("Uploading file to Gemini...")

        try:
            # Upload to Gemini
            myfile = genai.upload_file(temp_filename, mime_type="audio/mpeg")
            
            status_text.text("Processing audio (this may take a moment)...")
            
            # Wait for processing
            while myfile.state.name == "PROCESSING":
                time.sleep(2)
                myfile = genai.get_file(myfile.name)

            # Generate Content
            status_text.text("Generating insights...")
            model = genai.GenerativeModel('gemini-2.5-flash')
            
            prompt = """
            Listen to this recording. 
            Output a JSON object with two keys: "summary" (a string) and "action_items" (a list of strings).
            Example format:
            {
              "summary": "The meeting discussed...",
              "action_items": ["John to do X", "Sarah to do Y"]
            }
            """
            
            response = model.generate_content([myfile, prompt])
            
            # Parse Response
            cleaned_text = response.text.replace("```json", "").replace("```", "").strip()
            json_data = json.loads(cleaned_text)

            # --- Display Results in Browser ---
            st.success("Processing Complete!")
            status_text.empty() # Clear status message

            st.header("📋 Summary")
            st.write(json_data.get("summary", "No summary available."))

            st.header("✅ Action Items")
            # Convert action items to a clean list for display
            action_items = json_data.get("action_items", [])
            if action_items:
                for item in action_items:
                    st.markdown(f"- {item}")
            else:
                st.write("No specific action items detected.")

            # --- Prepare Excel for Download ---
            excel_data = []
            excel_data.append({
                "Category": "Meeting Summary", 
                "Content": json_data.get("summary", "No summary provided")
            })
            for item in action_items:
                excel_data.append({
                    "Category": "Action Item", 
                    "Content": item
                })
            
            df = pd.DataFrame(excel_data)
            output_excel_path = "meeting_report.xlsx"
            df.to_excel(output_excel_path, index=False)

            # Create Download Button
            with open(output_excel_path, "rb") as file:
                st.download_button(
                    label="📥 Download Excel Report",
                    data=file,
                    file_name="meeting_report.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                )

        except Exception as e:
            st.error(f"An error occurred: {e}")
