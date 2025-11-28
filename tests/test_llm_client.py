import json
from unittest.mock import Mock

import pytest

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

    import importlib, sys, types
    fake_google = types.SimpleNamespace(genai=Mock())
    fake_google.genai.Client.return_value = FakeClient()
    monkeypatch.setitem(sys.modules, 'google', fake_google)
    # ensure llm_client reloads google import
    import importlib
    mod = importlib.reload(importlib.import_module('llm_client'))

    resp = generate_content('Hello Gem')
    assert resp.text == 'hello from gemini'
    assert isinstance(resp.function_calls, list)
