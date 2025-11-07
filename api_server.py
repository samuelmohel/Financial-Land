# api_server.py
from fastapi import FastAPI, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pathlib import Path
import tempfile

# Hugging Face
from transformers import pipeline

# ----------------------------
# Initialize HF QA/LLM pipeline
# ----------------------------
# For simplicity, we’ll use a text-generation model that works offline if downloaded
# Example: "tiiuae/falcon-7b-instruct" (requires a GPU if large)
# For CPU-friendly testing, use smaller models like "bigscience/bloom-560m"
generator = pipeline(
    "text-generation",
    model="bigscience/bloom-560m",  # choose a small CPU-compatible model
    max_length=512,                 # limit response length
    do_sample=True,
    temperature=0.4,
)

# ----------------------------
# FastAPI app
# ----------------------------
app = FastAPI(title="FinWise Backend - HF Version")

# Allow Streamlit frontend to access this API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory storage for uploaded files per user
USER_DOCS = {}

# ----------------------------
# Upload document endpoint
# ----------------------------
@app.post("/upload_document")
async def upload_document(file: UploadFile = File(...), user_id: str = Form("anonymous")):
    """Handles uploaded PDFs or images and stores them temporarily."""
    try:
        suffix = Path(file.filename).suffix
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=suffix)
        tmp.write(await file.read())
        tmp.close()

        # Store path in memory
        USER_DOCS[user_id] = tmp.name
        return {"message": "File uploaded successfully", "user_id": user_id, "file_path": tmp.name}
    except Exception as e:
        return {"error": str(e)}

# ----------------------------
# Ask endpoint
# ----------------------------
@app.post("/ask")
async def ask(question: str = Form(...), user_id: str = Form("anonymous")):
    """Handles financial or land-related questions using Hugging Face model."""
    try:
        context = ""
        if user_id in USER_DOCS:
            context = f"The user uploaded a document at {USER_DOCS[user_id]}. You may refer to it as a source of financial or land-related information."

        system_prompt = (
            "You are FinWise, a financial and land advisor. "
            "You help users analyze bank statements, property documents, and finance-related questions. "
            "Be clear, factual, and provide helpful insights."
        )

        prompt = f"{system_prompt}\n{context}\nQuestion: {question}"

        # Generate response using Hugging Face model
        output = generator(prompt, max_length=512, do_sample=True, temperature=0.4)
        answer = output[0]["generated_text"]

        # Optional: strip repeated prompt from generated text
        if prompt in answer:
            answer = answer.replace(prompt, "").strip()

        return {"answer": answer}
    except Exception as e:
        return {"error": str(e)}
