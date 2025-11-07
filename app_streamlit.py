# app_streamlit.py
import streamlit as st
import requests
from pathlib import Path

# -------------------------------
# Backend API URL
# -------------------------------
API_URL = "http://localhost:8000"

# -------------------------------
# Streamlit Page Config
# -------------------------------
st.set_page_config(page_title="FinWise Agent", layout="wide")
st.title("💬 FinWise — Land & Finance Assistant")

st.markdown(
    """
    Welcome to **FinWise**, your intelligent assistant for:
    - 📜 Land and property document analysis  
    - 💰 Financial and banking questions  
    - 📊 Real-time insights from uploaded files  

    **Upload a document**, or just ask your question below 👇
    """
)

# -------------------------------
# User Info
# -------------------------------
user_id = st.text_input("Enter your user ID (optional):", value="guest")

# -------------------------------
# File Upload Section
# -------------------------------
st.subheader("📁 Upload your document")
uploaded = st.file_uploader(
    "Upload a land deed, financial record, or statement",
    type=["pdf", "png", "jpg", "jpeg"]
)

if uploaded is not None:
    # Save uploaded file temporarily
    tmp_path = f"temp_upload_{uploaded.name}"
    with open(tmp_path, "wb") as f:
        f.write(uploaded.getbuffer())

    # Send file to backend API
    with st.spinner("Uploading your document..."):
        try:
            files = {"file": open(tmp_path, "rb")}
            data = {"user_id": user_id}
            res = requests.post(f"{API_URL}/upload_document", files=files, data=data)

            if res.status_code == 200:
                st.success("✅ File uploaded successfully!")
                st.json(res.json())
            else:
                st.error(f"❌ Upload failed: {res.text}")
        except Exception as e:
            st.error(f"Error uploading file: {e}")

# -------------------------------
# Question Input Section
# -------------------------------
st.subheader("💬 Ask FinWise a Question")

topic = st.radio(
    "Choose a topic hint (optional, improves accuracy):",
    ["Auto-detect", "Land", "Finance"],
    horizontal=True
)

question = st.text_input(
    "Ask your question:",
    placeholder="e.g. What are the key risks in this land document? or Convert 100 USD to NGN"
)

if st.button("Send"):
    if not question.strip():
        st.warning("Please enter a question before sending.")
    else:
        with st.spinner("FinWise is thinking... 🤔"):
            try:
                payload = {
                    "question": question if topic == "Auto-detect" else f"(topic:{topic}) {question}",
                    "user_id": user_id,
                }
                res = requests.post(f"{API_URL}/ask", data=payload)

                if res.status_code == 200:
                    data = res.json()
                    if "answer" in data:
                        st.success("✅ Answer:")
                        st.write(data["answer"])
                    else:
                        st.error(data.get("error", "Unknown error"))
                else:
                    st.error(f"Server error: {res.text}")
            except Exception as e:
                st.error(f"Connection error: {e}")

# -------------------------------
# Footer
# -------------------------------
st.markdown("---")
st.caption("🤖 Powered by OpenAI & FinWise Agent | Built with Streamlit + FastAPI")
