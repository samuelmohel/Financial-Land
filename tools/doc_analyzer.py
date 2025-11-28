import logging

def process_document(file_path: str, company_id: str, doc_type: str) -> list[dict]:
    """
    Parses a document (PDF), splits it into semantic chunks, and extracts metadata.

    Args:
        file_path: Local path to the document.
        company_id: Identifier for metadata tagging.
        doc_type: Type of document (e.g., 'Annual Report', 'Invoice').

    Returns:
        A list of dictionaries, where each dict is a chunk with its metadata.
    """
    logger = logging.getLogger(__name__)
    logger.info("Starting analysis for: %s", file_path)
    
    # --- 1. Parsing (Placeholder) ---
    raw_text = "This is the extracted text from the document. Q3 net revenue was $500M."
    # In a real app, use pypdf or a library to extract text
    
    # --- 2. Chunking (Placeholder) ---
    # This process is critical: chunks must retain semantic context
    chunks = [
        raw_text[:40], 
        raw_text[40:]
    ]
    
    indexed_chunks = []
    for i, chunk in enumerate(chunks):
        indexed_chunks.append({
            "id": f"{company_id}_{doc_type}_{i}",
            "text": chunk,
            "metadata": {
                "company": company_id,
                "type": doc_type,
                "page": i + 1, # Placeholder for page number
                "date": "2024-09-30" 
            }
        })
        
    logger.info("Successfully chunked into %d pieces.", len(indexed_chunks))
    return indexed_chunks

if __name__ == '__main__':
    # Example usage
    chunks = process_document("temp/Q3_report.pdf", "COMPX", "EARNINGS")