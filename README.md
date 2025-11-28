**Financial-Land AI** is an advanced intelligence platform designed to revolutionize financial analysis. It leverages an **AI Agent** powered by **Retrieval Augmented Generation (RAG)** and specialized tools to analyze diverse financial data—including proprietary documents and real-time market data—providing users with accurate, auditable, and context-aware answers to complex queries.

## ✨ Core Features

* **AI Agent Orchestration:** An intelligent controller (`agent_controller.py`) that uses the **Gemini API** to dynamically decide when to call RAG for internal document knowledge or specialized tools for real-time data.
* **Retrieval Augmented Generation (RAG):** Ability to ingest and index proprietary financial documents (via `doc_analyzer.py` and `rag_retriever.py`) and generate answers grounded *only* in the content of those documents.
* **Specialized Tooling:** Integration with callable tools for real-time data execution:
    * **Currency Conversion** (`currency_tool.py`)
    * **OCR** for document ingestion (`ocr_tool.py`)
    * **Company Registry Check** (`registry_check.py`)
* **Auditable Traceability:** The `audit.py` module ensures every decision, source document, and calculation is logged, meeting high compliance standards for financial applications.
* **High-Performance Backend:** Built with **FastAPI** for a robust and scalable API service.
* **Interactive Frontend:** A dedicated data dashboard built with **Streamlit** (`app_streamlit.py`).

## 🛠️ Installation and Setup

### 1. Clone the Repository

```bash
git clone [https://github.com/samuelmohel/Financial-Land.git](https://github.com/samuelmohel/Financial-Land.git)
cd Financial-Land

### 3. Environment Variables

This project uses a `.env` file to manage sensitive configuration like API keys. Copy `.env.example` to `.env` and supply your secrets. Example important environment variables:

- `GEMINI_API_KEY` – Gemini API key used for model calls.
- `FINANCIAL_DATA_API_KEY` – API key for structured financial data (sometimes used as exchange-api key)
- `EXCHANGE_RATE_BASE_URL` – Base URL for exchange rate provider, e.g. `https://v6.exchangerate-api.com/v6`
- `EXCHANGE_RATE_API_KEY` – Optional provider-specific API key if the provider requires it in path or header.
 - `LLM_PROVIDER` – Which LLM provider to use (gemini or groq). Defaults to `gemini`.
 - `GROQ_API_KEY` – If using Groq, set your API key here.
 - `GROQ_MODEL` – The Groq model to use (e.g. `groq-1.0`).

After editing `.env`, keep it secret and ensure it's included in `.gitignore` to avoid accidental commits.

Using Groq or Gemini
- To use Groq: set `LLM_PROVIDER=groq`, `GROQ_API_KEY` and `GROQ_MODEL` in your `.env`. The app will use Groq for generation and parse a JSON snippet in the model output for function calls.
- To use Gemini: set `LLM_PROVIDER=gemini` and `GEMINI_API_KEY` in your `.env`. This is the default provider.