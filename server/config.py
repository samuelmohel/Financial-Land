# server/config.py
import os
from dotenv import load_dotenv
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-70b-versatile")
CHROMA_DIR = os.getenv("CHROMA_DIR", "./.chroma")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./finwise_audit.db")
S3_BUCKET = os.getenv("S3_BUCKET", "")
MAX_OCR_PAGES = int(os.getenv("MAX_OCR_PAGES", "10"))
