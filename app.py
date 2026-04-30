import streamlit as st
import pandas as pd
import google.generativeai as genai
import os

# --- Page Config ---
st.set_page_config(page_title="Noon Data Copilot", page_icon="🔍")
st.title("🔍 Noon Data Dictionary Copilot")
st.markdown("Ask me where to find the data you need!")

# --- 1. Load the Data from Google Sheets ---
# The @st.cache_data decorator ensures we only fetch the sheet once per hour, making the app blazing fast.
@st.cache_data(ttl=3600)
def load_data():
    # REPLACE THIS URL with your published CSV link
    csv_url = "https://docs.google.com/spreadsheets/d/e/2PACX-1vSlVS1JxK9kak88lkbvB5CkMDYNWw5tyUjO8JPvEdQX96su1lXQ7PCTP-wS34ehY9NFKnuitP1fh-4q/pub?gid=0&single=true&output=csv"
    df = pd.read_csv(csv_url, on_bad_lines='skip')
    df = df.dropna(subset=['Table_Name'])
    # Convert the entire dataframe to a CSV string to feed to the LLM
    return df.to_csv(index=False)

try:
    catalog_context = load_data()
except Exception as e:
    st.error(f"Failed to load Google Sheet: {e}")
    st.stop()

# --- 2. Initialize Gemini API ---
# We securely pull the API key from Streamlit's secrets manager
api_key = st.secrets["GEMINI_API_KEY"]
genai.configure(api_key=api_key)

# Configure the model instructions
generation_config = {
  "temperature": 0.0, # Keep it strictly factual, no hallucinating tables
}

system_instruction = f"""
You are a Senior Data Engineer at an e-commerce company. Your job is to help analysts find the right database tables.
Here is the complete metadata for all our tables:
---
{catalog_context}
---
When a user asks a question, tell them:
1. The exact Table Name(s) they should use.
2. The Primary Keys they should use to join or group the data.
3. A brief explanation of why this table solves their problem based on the description.

If the requested data does not exist in the provided catalog, say 'I cannot find a table for this metric in our current catalog.' Do not make up tables.
"""

model = genai.GenerativeModel(
    model_name="gemini-2.5-flash", # <-- Update this exactly!
    generation_config=generation_config,
    system_instruction=system_instruction
)

# --- 3. Streamlit Chat Interface ---
# Initialize chat history
if "messages" not in st.session_state:
    st.session_state.messages = []

# Display chat messages from history
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# React to user input
if prompt := st.chat_input("E.g., Which table has the daily return rate for FBN orders?"):
    # Display user message
    st.chat_message("user").markdown(prompt)
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Call Gemini API
    with st.chat_message("assistant"):
        with st.spinner("Searching the data catalog..."):
            # We send the user's prompt. The system instruction already contains the entire Google Sheet.
            try:
    # Try to ask the AI
    response = model.generate_content(prompt)
    st.write(response.text)

    except Exception as e:
    # If it crashes, intercept the error
    if "ResourceExhausted" in str(e):
        st.error("⏳ **AI resource limits reached.** The Copilot is out of quota for today. Please try again tomorrow!")
    else:
        st.error("⚠️ **Oops!** The Copilot encountered a temporary issue. Please try again in a minute.")
            
    # Add assistant response to chat history
    st.session_state.messages.append({"role": "assistant", "content": response.text})
