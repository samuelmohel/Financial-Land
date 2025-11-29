import json
import logging
from typing import Any, List, Optional
import time

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


def generate_content(prompt: str, model: Optional[str] = None, tools: Optional[dict] = None) -> LLMResponse:
    provider = settings.LLM_PROVIDER.lower()
    if provider == 'groq':
        return _generate_groq(prompt, model, tools)
    elif provider == 'gemini':
        return _generate_gemini(prompt, model, tools)
    else:
        raise ValueError(f"Unsupported LLM provider: {provider}")


def _generate_groq(prompt: str, model: Optional[str] = None, tools: Optional[dict] = None) -> LLMResponse:
    # Prevent accidentally passing Gemini model names to the Groq endpoint.
    # If a caller provided a model that looks like a Gemini model (e.g. 'gemini-...'),
    # fall back to the configured GROQ_MODEL to avoid misrouting requests.
    if model and isinstance(model, str) and 'gemini' in model.lower():
        logger.warning("Model name '%s' looks like a Gemini model; using GROQ_MODEL instead", model)
        model = None

    model = model or settings.GROQ_MODEL
    api_key = settings.GROQ_API_KEY
    if not api_key:
        raise RuntimeError("GROQ_API_KEY not configured in settings")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
    # If tools are provided, describe them and instruct the model to output JSON
    if tools:
        # Build a short description for each tool
        tool_descriptions = []
        for tname, tfunc in tools.items():
            try:
                import inspect
                sig = inspect.signature(tfunc)
                params = ', '.join([p for p in sig.parameters.keys()])
            except Exception:
                params = ''
            tool_descriptions.append(f"{tname}({params})")
        tool_text = "Available tools:\n" + "\n".join(tool_descriptions)
        # Instruction: ask to output JSON when calling a tool
        instruction = (
            "If you must call a tool to answer the user's query, respond with a single JSON object only. "
            "The object must have 'tool' and 'args' properties like: {\"tool\": \"get_exchange_rate\", \"args\": {\"source_currency\": \"USD\", \"target_currency\": \"NGN\"}}.\n"
            "If you do not need a tool, respond with final text answer.\n"
        )
        prompt = instruction + tool_text + "\nUSER QUERY:\n" + prompt

    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7
    }

    logger.debug("Calling Groq model %s", model)
    r = requests.post(url, json=payload, headers=headers, timeout=30)
    try:
        r.raise_for_status()
        data = r.json()
    except Exception:
        # Log detailed response body to help debugging 4xx/5xx errors from Groq
        body_text = None
        body_json = None
        try:
            body_text = r.text
        except Exception:
            body_text = '<could not read response body>'
        logger.error("Groq API returned error %s: %s", getattr(r, 'status_code', 'N/A'), body_text)

        # Try to parse JSON body to detect decommissioned model errors and retry with fallbacks
        try:
            body_json = r.json()
        except Exception:
            body_json = None

        code = None
        message = ''
        if isinstance(body_json, dict):
            err = body_json.get('error') or {}
            if isinstance(err, dict):
                code = err.get('code')
                message = err.get('message', '')
            else:
                message = str(err)

        # If model was decommissioned, attempt fallback models
        if code == 'model_decommissioned' or 'decommission' in (message or '').lower():
            # Use configured fallback list if present, otherwise default list
            fallback_models = getattr(settings, 'GROQ_FALLBACK_MODELS', [])
            if settings.GROQ_MODEL not in fallback_models:
                fallback_models = [settings.GROQ_MODEL] + list(fallback_models)
            # Ensure uniqueness and preserve order
            seen = set()
            fallback_models = [m for m in fallback_models if m and (m not in seen and not seen.add(m))]

            for fb in fallback_models:
                if fb == model:
                    continue

        # If this is a rate limit / quota error, attempt retry with smaller/faster model
        if getattr(r, 'status_code', None) == 429 or (code == 'RESOURCE_EXHAUSTED') or ('rate_limit' in (message or '').lower()):
            rate_fallback_models = ['llama-3.1-8b-instant', 'llama-3.3-70b-versatile', 'groq-1.0']
            for i, fb in enumerate(rate_fallback_models):
                if fb == model:
                    continue
                logger.info("Rate-limited by Groq; retrying with model: %s", fb)
                payload['model'] = fb
                time.sleep(0.5 * (i + 1))
                try:
                    rr = requests.post(url, json=payload, headers=headers, timeout=30)
                    rr.raise_for_status()
                    data = rr.json()
                    model = fb
                    r = rr
                    break
                except Exception:
                    logger.warning("Retry with %s failed", fb)
                    continue
                logger.info("Retrying Groq request with fallback model '%s' due to decommissioned model", fb)
                payload['model'] = fb
                try:
                    r = requests.post(url, json=payload, headers=headers, timeout=30)
                    r.raise_for_status()
                    data = r.json()
                    model = fb
                    break
                except Exception:
                    # Log and try next fallback
                    try:
                        logger.warning("Fallback model '%s' failed: %s", fb, r.text)
                    except Exception:
                        logger.warning("Fallback model '%s' failed (no body available)", fb)
                    continue

        # If we did not obtain a successful response after retries, re-raise original exception
        if 'data' not in locals():
            raise
        
    # Check for rate-limited responses (HTTP 429 or RESOURCE_EXHAUSTED) and retry with lightweight models
    if getattr(r, 'status_code', None) == 429 or (isinstance(data, dict) and \
            ((data.get('error') and (data['error'].get('status') == 'RESOURCE_EXHAUSTED' or 'rate_limit' in str(data['error']).lower())) or 'rate_limit' in json.dumps(data).lower())):
        # Try fallback order: smaller Llama > configured groq fallbacks
        default_rate_fallbacks = ['llama-3.1-8b-instant', 'llama-3.3-70b-versatile', 'groq-1.0']
        rate_fallback_models = list(getattr(settings, 'GROQ_FALLBACK_MODELS', default_rate_fallbacks))
        for i, fb in enumerate(rate_fallback_models):
            if fb == model:
                continue
            logger.info("Rate-limited by Groq; retrying with fallback model: %s", fb)
            payload['model'] = fb
            # backoff: short increasing delay
            time.sleep(0.5 * (i + 1))
            try:
                r = requests.post(url, json=payload, headers=headers, timeout=30)
                r.raise_for_status()
                data = r.json()
                model = fb
                break
            except Exception:
                logger.warning("Fallback model '%s' also failed (rate-limit or other).", fb)
                continue
    
    # Parse Groq OpenAI-compatible response format
    text = ""
    if "choices" in data and len(data["choices"]) > 0:
        choice = data["choices"][0]
        if "message" in choice:
            text = choice["message"].get("content", "")
        elif "text" in choice:
            text = choice.get("text", "")

    # Fallback: older Groq shapes may provide `output_text` or `output`.
    if not text:
        text = data.get('output_text') or ''
        if not text and 'output' in data:
            out = data['output']
            if isinstance(out, list) and out:
                if isinstance(out[0], dict):
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


def _generate_gemini(prompt: str, model: Optional[str] = None, tools: Optional[dict] = None) -> LLMResponse:
    try:
        from google import genai
    except Exception as exc:
        raise RuntimeError("genai SDK not available") from exc

    model = model or settings.RAG_MODEL
    if not settings.GEMINI_API_KEY:
        raise RuntimeError("GEMINI_API_KEY not configured in settings")
    client = genai.Client(api_key=settings.GEMINI_API_KEY)
    # genai SDK: keep the same behavior that was used previously
    # The genai SDK may support function calling via specialized params; for simplicity
    # we rely on the LLM to include function calls in `resp.function_calls` when needed.
    resp = client.models.generate_content(model=model, contents=prompt)
    # Map to LLMResponse
    text = getattr(resp, 'text', '')
    function_calls = []
    # Map function calls if present
    if getattr(resp, 'function_calls', None):
        function_calls = list(resp.function_calls)
    return LLMResponse(text=text, function_calls=function_calls)
