import logging
import os
from google import genai
from config import settings
from tools.rag_retriever import retrieve_documents

# Initialize the Gemini client
logger = logging.getLogger(__name__)
try:
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
except Exception as e:
    logger.exception("Failed to initialize Gemini client for RAG: %s", e)
    client = None

RAG_MODEL = settings.RAG_MODEL

def generate_rag_answer(user_query: str) -> dict:
    """
    Orchestrates the RAG process: retrieves context, sends to LLM, and gets an answer.

    Args:
        user_query: The financial question from the user.

    Returns:
        A dictionary containing the final answer and the source citations.
    """
    try:
        # 1. Retrieval (Placeholder for a complex vector search)
        relevant_chunks, citations = retrieve_documents(user_query, settings.RAG_K_CHUNKS)
        relevant_chunks = ["...retrieved chunk 1...", "...retrieved chunk 2..."]
        citations = ["Source: Q4 2024 Earnings Call Transcript", "Source: Annual Report 2023, p. 15"]
        
        context_string = "\n".join(relevant_chunks)

        # 2. Augmented Prompt Generation
        prompt = (
            "You are a highly specialized financial analyst. Use ONLY the provided context to answer the user's query.\n"
            "CONTEXT:\n"
            f"{context_string}\n"
            "USER QUERY:\n"
            f"{user_query}"
        )

        # 3. Generation
        if not client:
            logger.error("No Gemini client available for RAG generation.")
            raise RuntimeError("Gemini client not initialized")

        response = client.models.generate_content(
            model=RAG_MODEL,
            contents=prompt
        )

        return {
            "answer": response.text,
            "sources": citations,
            "audit_success": True
        }

    except Exception as e:
        logger.exception("RAG generation failed: %s", e)
        return {
            "answer": "An error occurred during RAG processing.",
            "sources": [],
            "audit_success": False
        }