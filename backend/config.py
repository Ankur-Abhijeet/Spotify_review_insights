import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    LLM_PROVIDER: str = "ollama"
    OLLAMA_BASE_URL: str = "http://localhost:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    GROQ_API_KEY: str = ""
    GROQ_MODEL: str = "llama-3.1-8b-instant"
    LLM_BATCH_SIZE: int = 20
    DAILY_TOKEN_LIMIT: int = 500000
    DAILY_CALL_LIMIT: int = 1000

    RAG_EMBEDDING_MODEL: str = "nomic-embed-text"
    RAG_TOP_K: int = 15

    SCRAPER_HEADLESS: bool = True
    SCRAPER_DELAY_MS_MIN: int = 500
    SCRAPER_DELAY_MS_MAX: int = 2000
    REDDIT_FETCH_COMMENTS: bool = False

    DATA_DIR: str = "../data"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    
    # Needs to be list or set for fastapi cors middleware, parsing from comma-separated string
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

settings = Settings()
