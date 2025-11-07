# server/tools/doc_analyzer.py
import re
from typing import Dict, Any


def extract_basic_fields(full_text: str) -> Dict[str, Any]:
    # Simple regex-based extraction for MVP — tune for your documents
    dates = re.findall(r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b", full_text)
    names = re.findall(r"(?:Owner|Proprietor|Name)\s*[:\-]\s*([A-Z][A-Za-z ,\.]+)", full_text)
    survey = re.findall(r"(Survey|Plot)\s*No\.*\s*[:\-]?\s*([A-Za-z0-9\-\/]+)", full_text, re.IGNORECASE)
    return {"dates": dates, "names": names, "survey": survey}