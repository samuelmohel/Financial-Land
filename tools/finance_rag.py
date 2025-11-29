import logging
from config import settings
from llm_client import generate_content
from tools.rag_retriever import retrieve_documents

logger = logging.getLogger(__name__)
# No SDK client initialization here; use provider-agnostic `generate_content` in llm_client

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

        # 3. Generation - use the provider-agnostic generate_content wrapper
        response = generate_content(prompt, model=RAG_MODEL)

        return {
            "answer": getattr(response, 'text', str(response)),
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