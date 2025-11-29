from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal
from typing import List

class Settings(BaseSettings):
    """
    Centralized configuration management for the Financial-Land project.
    """
    model_config = SettingsConfigDict(
        env_file='.env',
        extra='ignore'
    )

    # Core Application Settings
    APP_NAME: str = "Financial Land AI"
    ENVIRONMENT: Literal['dev', 'prod'] = 'dev'
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # AI & API Keys (Loaded from .env)
    GEMINI_API_KEY: str = ''
    FINANCIAL_DATA_API_KEY: str = ''

    # RAG Settings
    VECTOR_DB_URL: str = "http://localhost:8080"
    RAG_MODEL: str = "llama-3.3-70b-versatile"
    RAG_K_CHUNKS: int = 5
    # External API configuration for currency exchange provider
    EXCHANGE_RATE_BASE_URL: str = "https://v6.exchangerate-api.com/v6"
    EXCHANGE_RATE_API_KEY: str = ""
    # LLM Provider configuration
    LLM_PROVIDER: Literal['gemini', 'groq'] = 'groq'
    GROQ_API_KEY: str = ''
    GROQ_MODEL: str = 'llama-3.3-70b-versatile'  # Default Groq model (Llama 3.3 70B versatile recommended for free tier)
    GROQ_FALLBACK_MODELS: List[str] = ['llama-3.3-70b-versatile', 'llama-3.1-8b-instant', 'groq-1.0']
    # Optional external registry API endpoint for validating company details
    REGISTRY_API_URL: str = ""

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == 'prod'

# Initialize settings object to be imported across the project
settings = Settings()