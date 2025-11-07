# server/agent_controller.py
from langchain.chat_models import ChatOpenAI
from langchain.agents import Tool, initialize_agent, AgentType
from server.tools.ocr_tool import pdf_to_text
from server.tools.doc_analyzer import extract_basic_fields
from server.tools.registry_check import check_registry_by_survey
from server.tools.rag_retriever import retrieve
from server.tools.currency_tool import convert_currency
from server.tools.finance_rag import search_finance
from server.audit import log
from server.config import OPENAI_API_KEY

# LLM (OpenAI used here; swap to Groq client where needed)
llm = ChatOpenAI(openai_api_key=OPENAI_API_KEY, temperature=0)


def doc_analyze_tool(file_path: str):
    out = pdf_to_text(file_path)
    text = "\n".join([p.get("text", "") for p in out["pages"] if p.get("text")])
    fields = extract_basic_fields(text)
    log("doc_analyze", {"file": file_path, "fields": fields})
    return {"text": text, "fields": fields}


def registry_tool(survey_id: str):
    res = check_registry_by_survey(survey_id)
    return res


def rag_tool(query: str):
    hits = retrieve(query)
    return [{"page_content": d.page_content, "metadata": d.metadata} for d in hits]


def currency_tool(amount: float, from_currency: str, to_currency: str):
    return convert_currency(amount, from_currency, to_currency)


def finance_rag_tool(query: str):
    return search_finance(query)


# Wrap as LangChain Tools
tools = [
    Tool(name="DocumentAnalyzer", func=doc_analyze_tool, description="Given a file path, returns extracted text and fields."),
    Tool(name="RegistryCheck", func=registry_tool, description="Check registry by survey/identifier."),
    Tool(name="LandRAG", func=rag_tool, description="Search land law and registry KB."),
    Tool(name="CurrencyConverter", func=currency_tool, description="Convert currency between two units."),
    Tool(name="FinanceRAG", func=finance_rag_tool, description="Search financial knowledge base."),
]

agent = initialize_agent(tools, llm, agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION, verbose=True)


def run_agent(user_message: str, user_id: str | None = None):
    log("agent_start", {"query": user_message}, user_id=user_id)
    result = agent.run(user_message)
    log("agent_finish", {"result": result}, user_id=user_id)
    return result
