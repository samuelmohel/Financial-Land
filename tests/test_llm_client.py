from unittest.mock import Mock

from config import settings


def test_groq_generate_content_parses_json(monkeypatch):
    from llm_client import generate_content

    # Arrange: make provider Groq and set mock API key
    settings.LLM_PROVIDER = 'groq'
    settings.GROQ_API_KEY = 'mock-key'
    settings.GROQ_MODEL = 'mock-model'

    sample_text = 'Result data\n{"tool":"get_exchange_rate","args":{"source_currency":"USD","target_currency":"NGN"}}\nEnd'
    mock_response_json = {'output_text': sample_text}

    def fake_post(url, json=None, headers=None, timeout=30):
        class Resp:
            def raise_for_status(self):
                return None

            def json(self):
                return mock_response_json

        return Resp()

    monkeypatch.setattr('llm_client.requests.post', fake_post)

    # Act
    resp = generate_content('Please call the tool in JSON format')

    # Assert
    assert isinstance(resp.text, str)
    assert resp.function_calls and isinstance(resp.function_calls, list)
    assert resp.function_calls[0]['tool'] == 'get_exchange_rate'


def test_gemini_generate_content_uses_genai(monkeypatch):
    from llm_client import generate_content

    settings.LLM_PROVIDER = 'gemini'
    settings.GEMINI_API_KEY = 'fake_gem_key'
    settings.RAG_MODEL = 'gemini- test'

    class FakeResp:
        def __init__(self):
            self.text = 'hello from gemini'
            self.function_calls = []

    class FakeModels:
        def __init__(self):
            pass

        def generate_content(self, model, contents):
            return FakeResp()

    class FakeClient:
        def __init__(self, api_key=None):
            self.models = FakeModels()

    import importlib
    import sys
    import types
    fake_google = types.SimpleNamespace(genai=Mock())
    fake_google.genai.Client.return_value = FakeClient()
    monkeypatch.setitem(sys.modules, 'google', fake_google)
    # ensure llm_client reloads google import
    importlib.reload(importlib.import_module('llm_client'))

    resp = generate_content('Hello Gem')
    assert resp.text == 'hello from gemini'
    assert isinstance(resp.function_calls, list)


def test_groq_rate_limit_fallback(monkeypatch):
    from llm_client import generate_content
    import requests

    # Arrange
    settings.LLM_PROVIDER = 'groq'
    settings.GROQ_API_KEY = 'mock-key'
    settings.GROQ_MODEL = 'llama-3.3-70b-versatile'

    # First response: 429 Resource Exhausted
    error_body = {'error': {'code': 'RESOURCE_EXHAUSTED', 'message': 'You exceeded your current quota', 'status': 'RESOURCE_EXHAUSTED'}}
    good_body = {'choices': [{'message': {'content': 'Hello after fallback'}}]}

    state = {'calls': 0}

    def fake_post(url, json=None, headers=None, timeout=30):
        class Resp:
            def __init__(self, ok, status, body):
                self._ok = ok
                self.status_code = status
                self._body = body

            def raise_for_status(self):
                if not self._ok:
                    raise requests.exceptions.HTTPError("HTTP %s" % self.status_code)

            def json(self):
                return self._body

            @property
            def text(self):
                return str(self._body)

        state['calls'] += 1
        if state['calls'] == 1:
            return Resp(False, 429, error_body)
        else:
            return Resp(True, 200, good_body)

    monkeypatch.setattr('llm_client.requests.post', fake_post)

    # Act
    resp = generate_content('test rate limit fallback')

    # Assert
    assert isinstance(resp.text, str)
    assert resp.text == 'Hello after fallback'
