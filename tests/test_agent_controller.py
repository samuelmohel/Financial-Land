from unittest.mock import Mock
import pytest
from config import settings

import agent_controller


class DummyResp:
    def __init__(self, text='', function_calls=None):
        self.text = text
        self.function_calls = function_calls or []


def test_agent_calls_tool_when_groq_json_return(monkeypatch):
    settings.LLM_PROVIDER = 'groq'
    # No SDK client at module-level; make sure the agent uses wrappers

    seq = []

    def fake_generate_content(prompt, model=None, tools=None):
        if not seq:
            seq.append(1)
            # First call: instructs agent to call a tool via JSON
            return DummyResp(function_calls=[{'tool': 'get_exchange_rate', 'args': {'source_currency': 'USD', 'target_currency': 'NGN'}}])
        # Final synthesis
        return DummyResp(text='1 USD = 800 NGN')

    monkeypatch.setattr(agent_controller, 'generate_content', fake_generate_content)
    mock_get_rate = Mock(return_value=800)
    agent_controller.tools['get_exchange_rate'] = mock_get_rate

    result = agent_controller.process_query_with_agent('Please call the tool to convert USD to NGN')
    assert '1 USD' in result['final_answer']
    assert 'get_exchange_rate' in result['used_tools']
    assert 'tool_errors' in result and isinstance(result['tool_errors'], list)
    mock_get_rate.assert_called_once_with(source_currency='USD', target_currency='NGN')


def test_agent_handles_gemini_function_calls(monkeypatch):
    settings.LLM_PROVIDER = 'gemini'
    # Ensure any previous client flags don't affect flow
    if hasattr(agent_controller, 'client'):
        agent_controller.client = None

    class FakeCall:
        def __init__(self, name, args):
            self.name = name
            self.args = args

    seq = [
        DummyResp(function_calls=[FakeCall('get_exchange_rate', {'source_currency': 'USD', 'target_currency': 'NGN'})]),
        DummyResp(text='1 USD = 500 NGN')
    ]

    def fake_generate_content(prompt, model=None, tools=None):
        return seq.pop(0)

    monkeypatch.setattr(agent_controller, 'generate_content', fake_generate_content)
    mock_get_rate = Mock(return_value=500)
    agent_controller.tools['get_exchange_rate'] = mock_get_rate

    result = agent_controller.process_query_with_agent('Use the tool with gemini shape')
    assert '1 USD' in result['final_answer']
    assert 'get_exchange_rate' in result['used_tools']
    mock_get_rate.assert_called_once_with(source_currency='USD', target_currency='NGN')
    assert 'tool_errors' in result and isinstance(result['tool_errors'], list)


def test_agent_handles_multiple_tools(monkeypatch):
    settings.LLM_PROVIDER = 'groq'
    if hasattr(agent_controller, 'client'):
        agent_controller.client = None

    seq = []

    def fake_generate_content(prompt, model=None, tools=None):
        # initial call: request to call two tools
        if not seq:
            seq.append(1)
            return DummyResp(function_calls=[
                {'tool': 'get_exchange_rate', 'args': {'source_currency': 'USD', 'target_currency': 'NGN'}},
                {'tool': 'verify_company_registry', 'args': {'company_name': 'Acme Corp'}}
            ])
        # final synthesis
        return DummyResp(text='Results: rate and registry info')

    monkeypatch.setattr(agent_controller, 'generate_content', fake_generate_content)
    mock_get_rate = Mock(return_value=750)
    mock_verify = Mock(return_value={'valid': True})
    agent_controller.tools['get_exchange_rate'] = mock_get_rate
    agent_controller.tools['verify_company_registry'] = mock_verify

    result = agent_controller.process_query_with_agent('Call multiple tools')
    assert 'Results' in result['final_answer']
    assert 'get_exchange_rate' in result['used_tools'] and 'verify_company_registry' in result['used_tools']
    mock_get_rate.assert_called_once_with(source_currency='USD', target_currency='NGN')
    mock_verify.assert_called_once_with(company_name='Acme Corp')
    assert 'tool_errors' in result and isinstance(result['tool_errors'], list)


def test_agent_rejects_invalid_tool_args(monkeypatch):
    settings.LLM_PROVIDER = 'groq'
    if hasattr(agent_controller, 'client'):
        agent_controller.client = None

    seq = []

    def fake_generate_content(prompt, model=None, tools=None):
        if not seq:
            seq.append(1)
            # Missing target_currency
            return DummyResp(function_calls=[{'tool': 'get_exchange_rate', 'args': {'source_currency': 'USD'}}])
        return DummyResp(text='This should ignore tool and respond directly')

    monkeypatch.setattr(agent_controller, 'generate_content', fake_generate_content)
    mock_get_rate = Mock(return_value=900)
    agent_controller.tools['get_exchange_rate'] = mock_get_rate

    result = agent_controller.process_query_with_agent('Call tool with missing args')
    assert 'get_exchange_rate' in result['used_tools']
    # ensure the function was not called due to validation
    mock_get_rate.assert_not_called()
    assert 'tool_errors' in result and result['tool_errors']


def test_agent_rag_flow_calls_generate_rag_and_returns(monkeypatch):
    settings.LLM_PROVIDER = 'groq'
    if hasattr(agent_controller, 'client'):
        agent_controller.client = None

    seq = []

    def fake_generate_content(prompt, model=None, tools=None):
        if not seq:
            seq.append(1)
            return DummyResp(function_calls=[{'tool': 'generate_rag_answer', 'args': {'user_query': 'What is company revenue?'}}])
        return DummyResp(text='RAG final synthesis: Company revenue is $1M')

    monkeypatch.setattr(agent_controller, 'generate_content', fake_generate_content)
    mock_rag = Mock(return_value={'answer': 'Revenue is $1M', 'sources': ['doc1']})
    agent_controller.tools['generate_rag_answer'] = mock_rag

    result = agent_controller.process_query_with_agent('Please run RAG')
    assert 'RAG final synthesis' in result['final_answer']
    assert 'generate_rag_answer' in result['used_tools']
    mock_rag.assert_called_once_with(user_query='What is company revenue?')
    assert 'tool_errors' in result and isinstance(result['tool_errors'], list)


def test_agent_handles_failure_in_tool(monkeypatch):
    settings.LLM_PROVIDER = 'groq'
    if hasattr(agent_controller, 'client'):
        agent_controller.client = None

    seq = []

    def fake_generate_content(prompt, model=None, tools=None):
        if not seq:
            seq.append(1)
            return DummyResp(function_calls=[{'tool': 'get_exchange_rate', 'args': {'source_currency': 'USD', 'target_currency': 'NGN'}}])
        return DummyResp(text='Error handled')

    monkeypatch.setattr(agent_controller, 'generate_content', fake_generate_content)
    # Simulate network timeout causing exception in tool
    agent_controller.tools['get_exchange_rate'] = Mock(side_effect=Exception('timeout'))

    result = agent_controller.process_query_with_agent('Please convert 1 USD to NGN')
    assert 'get_exchange_rate' in result['used_tools']
    assert 'tool_errors' in result and any('timeout' in e for e in result['tool_errors'])


def test_get_exchange_rate_raises_tool_error(monkeypatch):
    from tools.currency_tool import get_exchange_rate, ToolExecutionError
    # Monkeypatch requests.get to raise RequestException
    import requests

    def fake_get(url, headers=None, timeout=5):
        class Resp:
            def raise_for_status(self):
                raise requests.exceptions.HTTPError('timeout')

        return Resp()

    monkeypatch.setattr('tools.currency_tool.requests.get', fake_get)
    with pytest.raises(ToolExecutionError):
        get_exchange_rate('USD', 'NGN')
