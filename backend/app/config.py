"""
Application configuration management via Pydantic settings.
"""

from typing import List, Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/lenny_growth"

    # Ollama Local Service
    ollama_base_url: str = "http://localhost:11434"
    embedding_model: str = "nomic-embed-text"
    llm_model: str = "llama3.1:8b"
    ollama_model: str = "llama3.1:8b"
    ollama_timeout: float = 180.0

    # LLM Router Settings
    llm_provider: str = "ollama"  # "ollama" | "cloud"

    # Cloud LLM Settings (free tiers: Groq or Gemini)
    cloud_llm_provider: str = "groq"  # "groq" | "gemini"
    cloud_llm_api_key: Optional[str] = None
    cloud_llm_model: str = "llama-3.3-70b-versatile"
    cloud_llm_base_url: Optional[str] = None

    # Specific Provider Key Aliases
    groq_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None

    @property
    def resolved_cloud_api_key(self) -> Optional[str]:
        if self.cloud_llm_api_key:
            return self.cloud_llm_api_key
        if self.cloud_llm_provider.lower() == "groq" and self.groq_api_key:
            return self.groq_api_key
        if self.cloud_llm_provider.lower() == "gemini" and self.gemini_api_key:
            return self.gemini_api_key
        return None

    # RAG Retrieval Settings
    rag_top_k: int = 4
    top_k_chunks: Optional[int] = None
    rag_similarity_threshold: float = 0.40
    similarity_threshold: Optional[float] = None
    rag_history_turns: int = 6

    @property
    def effective_top_k(self) -> int:
        return self.top_k_chunks if self.top_k_chunks is not None else self.rag_top_k

    @property
    def effective_similarity_threshold(self) -> float:
        return (
            self.similarity_threshold
            if self.similarity_threshold is not None
            else self.rag_similarity_threshold
        )

    # Ship 30 for 30 Skill Configuration
    ship30_target_word_count: int = 1250
    ship30_word_count_tolerance: float = 0.20

    # Server & Security
    backend_port: int = 8000
    cors_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
    ]
    app_env: str = "development"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()
