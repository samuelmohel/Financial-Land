from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Literal

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
    GEMINI_API_KEY: str
    FINANCIAL_DATA_API_KEY: str

    # RAG Settings
    VECTOR_DB_URL: str = "http://localhost:8080"
    RAG_MODEL: str = "gemini-2.5-flash"
    RAG_K_CHUNKS: int = 5
    # External API configuration for currency exchange provider
    EXCHANGE_RATE_BASE_URL: str = "https://v6.exchangerate-api.com/v6"
    EXCHANGE_RATE_API_KEY: str = ""
    # Optional external registry API endpoint for validating company details
    REGISTRY_API_URL: str = ""

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == 'prod'

# Initialize settings object to be imported across the project
settings = Settings()