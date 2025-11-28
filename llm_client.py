import json
import logging
import re
from typing import Any, List, Optional

import requests
from config import settings

logger = logging.getLogger(__name__)


class LLMResponse:
    def __init__(self, text: str, function_calls: Optional[List[Any]] = None):
        self.text = text
        self.function_calls = function_calls or []


def _extract_json_snippet(s: str) -> Optional[str]:
    # Finds first JSON object by scanning braces and returning the substring
    start = s.find('{')
    if start == -1:
        return None
    depth = 0
    for i in range(start, len(s)):
        c = s[i]
        if c == '{':
            depth += 1
        elif c == '}':
            depth -= 1
            if depth == 0:
                return s[start:i+1]
    return None


def generate_content(prompt: str, model: Optional[str] = None) -> LLMResponse:
    provider = settings.LLM_PROVIDER.lower()
    if provider == 'groq':
        return _generate_groq(prompt, model)
    elif provider == 'gemini':
        return _generate_gemini(prompt, model)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def _generate_groq(prompt: str, model: Optional[str] = None) -> LLMResponse:
    model = model or settings.GROQ_MODEL
    api_key = settings.GROQ_API_KEY
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not configured in settings")

    url = f"https://api.groq.ai/v1/models/{model}/infer"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    payload = {"input": prompt}

    logger.debug("Calling Groq model %s", model)
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    r.raise_for_status()
    data = r.json()
    # Groq may return model outputs in different shapes; look for 'output' or 'output_text'
    text = data.get('output_text') or ''
    if not text and 'output' in data:
        out = data['output']
        if isinstance(out, list) and out:
            if isinstance(out[0], dict):
                # e.g., out[0]['content'] or 'text'
                text = out[0].get('content') or out[0].get('text') or ''
            else:
                text = str(out[0])
        else:
            text = str(out)

    function_calls = []
    # If prompt instructed JSON function call, extract JSON snippet and parse
    json_snippet = _extract_json_snippet(text)
    if json_snippet:
        try:
            parsed = json.loads(json_snippet)
            # Make it a list of calls if not
            if isinstance(parsed, list):
                function_calls = parsed
            else:
                function_calls = [parsed]
        except json.JSONDecodeError:
            logger.debug("Groq output included JSON-looking snippet but failed parsing")

    return LLMResponse(text=text, function_calls=function_calls)


def _generate_gemini(prompt: str, model: Optional[str] = None) -> LLMResponse:
    try:
        from google import genai
    except Exception as exc:
        raise RuntimeError("genai SDK not available") from exc

    model = model or settings.RAG_MODEL
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not configured in settings")
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    # genai SDK: keep the same behavior that was used previously
    resp = client.models.generate_content(model=model, contents=prompt)
    # Map to LLMResponse
    text = getattr(resp, 'text', '')
    function_calls = []
    # Map function calls if present
    if getattr(resp, 'function_calls', None):
        function_calls = list(resp.function_calls)
    return LLMResponse(text=text, function_calls=function_calls)
