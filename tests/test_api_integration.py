from fastapi.testclient import TestClient
from unittest.mock import Mock

from main import app
from config import settings

client = TestClient(app)


def test_api_endpoint_handles_groq_tool_call(monkeypatch):
    settings.LLM_PROVIDER = 'groq'
    # Simulate llm_client returning a tool call and a final text
    class DummyResp:
        def __init__(self, text='', function_calls=None):
            self.text = text
            self.function_calls = function_calls or []

    seq = []

    def fake_generate_content(prompt, model=None, tools=None):
        if not seq:
            seq.append(1)
            return DummyResp(function_calls=[{'tool': 'get_exchange_rate', 'args': {'source_currency': 'USD', 'target_currency': 'NGN'}}])
        return DummyResp(text='1 USD = 800 NGN')

    import agent_controller
    monkeypatch.setattr(agent_controller, 'generate_content', fake_generate_content)
    # Patch tools
    import agent_controller
    agent_controller.tools['get_exchange_rate'] = Mock(return_value=800)

    resp = client.post('/v1/query', json={'query': 'Convert USD to NGN'})
    assert resp.status_code == 200
    data = resp.json()
    assert 'answer' in data and '1 USD' in data['answer']
    assert 'tools_used' in data and 'get_exchange_rate' in data['tools_used']
    assert 'tool_errors' in data and isinstance(data['tool_errors'], list) and data['tool_errors'] == []


def test_api_endpoint_handles_rag_tool(monkeypatch):
    settings.LLM_PROVIDER = 'groq'
    class DummyResp:
        def __init__(self, text='', function_calls=None):
            self.text = text
            self.function_calls = function_calls or []

    seq = []

    def fake_generate_content(prompt, model=None, tools=None):
        if not seq:
            seq.append(1)
            return DummyResp(function_calls=[{'tool': 'generate_rag_answer', 'args': {'user_query': 'Tell me revenue'}}])
        return DummyResp(text='RAG: revenue is $500M')

    import agent_controller
    monkeypatch.setattr(agent_controller, 'generate_content', fake_generate_content)
    import agent_controller
    agent_controller.tools['generate_rag_answer'] = Mock(return_value={'answer': 'Revenue: $500M', 'sources': []})

    resp = client.post('/v1/query', json={'query': 'Please run RAG'})
    assert resp.status_code == 200
    data = resp.json()
    assert 'RAG' in data['answer'] or 'Revenue' in data['answer']
    assert 'generate_rag_answer' in data['tools_used']
    assert 'tool_errors' in data and isinstance(data['tool_errors'], list) and data['tool_errors'] == []


def test_provider_endpoint_shows_config():
    from config import settings
    resp = client.get('/v1/provider')
    assert resp.status_code == 200
    data = resp.json()
    assert data['provider'] == settings.LLM_PROVIDER
    # model should be the GROQ model when using groq provider
    if settings.LLM_PROVIDER == 'groq':
        assert data['model'] == settings.GROQ_MODEL
    else:
        assert data['model'] == settings.RAG_MODEL
