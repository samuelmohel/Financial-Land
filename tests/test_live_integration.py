import os
import pytest
from config import settings

LIVE = os.getenv('LIVE_INTEGRATION', 'false').lower() in ('1', 'true', 'yes')


@pytest.mark.skipif(not LIVE, reason='Live integration tests disabled. Set LIVE_INTEGRATION=1 to run')
def test_live_groq_connectivity():
    from llm_client import generate_content
    assert settings.GROQ_API_KEY, 'GROQ_API_KEY must be set for live test'
    resp = generate_content('Hello from live Groq test', model=settings.GROQ_MODEL)
    assert getattr(resp, 'text', None) is not None


@pytest.mark.skipif(not LIVE, reason='Live integration tests disabled. Set LIVE_INTEGRATION=1 to run')
def test_live_end_to_end_agent():
    import agent_controller
    # Ensure the E2E query triggers tooling; the environment must have exchange rate key and vector DB if needed
    res = agent_controller.process_query_with_agent('Convert 1 USD to NGN')
    # The test asserts we got a valid response (may include tool_errors if an external tool failed)
    assert 'final_answer' in res
    assert 'used_tools' in res
