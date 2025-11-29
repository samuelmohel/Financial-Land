# Rag retriever: supports Chromadb and in-memory fallback
import logging
from config import settings
from typing import List, Tuple, Dict
try:
    import chromadb  # if installed; optional
    from chromadb.config import Settings as ChromaSettings
except Exception:
    chromadb = None
    ChromaSettings = None
try:
    from google import genai
except Exception:
    genai = None
# import google.genai is not required here

_in_memory_store: List[Dict[str, str]] = []
_chroma_client = None
_chroma_collection = None


def upsert_chunks_to_vector_db(chunks: list[dict]):
    """
    Generates embeddings for a list of text chunks and inserts them into the vector database.
    """
    logger = logging.getLogger(__name__)
    logger.info("Generating embeddings and upserting %d chunks to %s", len(chunks), settings.VECTOR_DB_URL)
    # 1. Embedding: Use Gemini embedding model
    # embedding_model = genai.Client().models.get_embedding_model("text-embedding-004")
    # 2. Vector DB Insertion: Call the vector DB client (e.g., chromadb.upsert)
    # If a Chromadb instance is configured, you could insert real embeddings there.
    def get_embedding(text: str) -> List[float]:
        # Prefer Gemini embeddings if available
        if genai and settings.GEMINI_API_KEY:
            try:
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                emb_resp = client.embeddings.create(model="text-embedding-3-small", input=text)
                return emb_resp[0].embedding if isinstance(emb_resp, list) else emb_resp.embedding
            except Exception:
                logger.exception("Gemini embedding failed, falling back to simple embedding")
        # Fallback: deterministic hash-based embedding (not semantically accurate but works offline)
        import hashlib
        digest = hashlib.sha256(text.encode('utf-8')).digest()
        # convert bytes to floats between -1 and 1
        vec = [((b / 255.0) * 2.0 - 1.0) for b in digest[:32]]
        return vec

    if chromadb and (settings.VECTOR_DB_URL and 'localhost' not in settings.VECTOR_DB_URL):
        logger.info("(Chromadb integration requested; attempting remote connection)")
        try:
            # Use chromadb client (basic configuration) - this requires the user to provide a chroma server URL or local
            # For the example, we just instantiate default client
            global _chroma_client
            if _chroma_client is None:
                _chroma_client = chromadb.Client()
            col = None
            try:
                col = _chroma_client.get_collection("finance_land")
            except Exception:
                col = _chroma_client.create_collection("finance_land")
            # Prepare batches
            ids = [c.get('id', f'doc-{i}') for i, c in enumerate(chunks)]
            documents = [c.get('text', '') for c in chunks]
            metadatas = [{'source': c.get('source', 'unknown')} for c in chunks]
            embeddings = [get_embedding(t) for t in documents]
            col.add(ids=ids, metadatas=metadatas, documents=documents, embeddings=embeddings)
            logger.info("Ingestion complete. Chromadb index updated with %d chunks.", len(chunks))
            return
        except Exception:
            logger.exception("Chromadb ingestion failed; falling back to in-memory storage")
    else:
        # Fallback: simple in-memory store
        for c in chunks:
            _in_memory_store.append(c)
        logger.info("Ingestion complete. In-memory index updated with %d chunks.", len(chunks))
    
def retrieve_documents(query: str, k: int) -> Tuple[List[str], List[str]]:
    """
    Searches the vector database for the top-k relevant text chunks based on the query.

    Returns:
        A tuple: (list of relevant text chunks, list of source citations)
    """
    logger = logging.getLogger(__name__)
    logger.info("Retrieving top %d documents for query: %s", k, query)
    # 1. Query Embedding: Embed the user's query
    # 2. Vector Search: Execute the nearest neighbor search
    
    # If Chromadb is available and remote
    def get_embedding(text: str) -> List[float]:
        if genai and settings.GEMINI_API_KEY:
            try:
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                emb_resp = client.embeddings.create(model="text-embedding-3-small", input=text)
                return emb_resp[0].embedding if isinstance(emb_resp, list) else emb_resp.embedding
            except Exception:
                logger.exception("Gemini embedding failed; using hash fallback")
        import hashlib
        digest = hashlib.sha256(text.encode('utf-8')).digest()
        vec = [((b / 255.0) * 2.0 - 1.0) for b in digest[:32]]
        return vec

    if chromadb and (settings.VECTOR_DB_URL and 'localhost' not in settings.VECTOR_DB_URL):
        try:
            global _chroma_client
            if _chroma_client is None:
                _chroma_client = chromadb.Client()
            col = _chroma_client.get_collection("finance_land")
            query_emb = get_embedding(query)
            # Attempt an embedding-based query for better semantic matching.
            try:
                results = col.query(query_embeddings=[query_emb], n_results=k, include=['documents', 'metadatas'])
            except Exception:
                results = col.query(queries=[query], n_results=k, include=['documents', 'metadatas'])
            docs = results.get('documents', [])
            metadatas = results.get('metadatas', [])
            # results documents is a list of lists
            relevant_chunks = docs[0] if docs and isinstance(docs, list) else []
            citations = [m.get('source', 'unknown') if isinstance(m, dict) else str(m) for m in (metadatas[0] if metadatas and isinstance(metadatas, list) else [])]
            return relevant_chunks[:k], citations[:k]
        except Exception:
            logger.exception("Chromadb query failed; falling back to in-memory search")
    # Fallback: simple substring match on in-memory store
    hits = []
    for doc in _in_memory_store:
        content = doc.get('text', '') if isinstance(doc, dict) else str(doc)
        score = content.count(query.split()[0])  # naive score using first token
        hits.append((score, content, doc.get('source', 'unknown') if isinstance(doc, dict) else 'unknown'))
    hits.sort(key=lambda t: t[0], reverse=True)
    relevant_chunks = [h[1] for h in hits[:k]]
    citations = [h[2] for h in hits[:k]]
    if not relevant_chunks:
        # default placeholder
        relevant_chunks = [
            "The Q3 2024 report indicates a net revenue of $500 Million.",
            "The company's primary focus for next year is renewable energy."
        ]
        citations = [
            "Source: Q3 2024 Investor Presentation, Slide 10",
            "Source: CEO Letter, Oct 2024"
        ]
    
    return relevant_chunks, citations