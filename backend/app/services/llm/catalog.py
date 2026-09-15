"""
Unified Model Registry & Catalog for The Lenny Growth Assistant.
Contains metadata for local and cloud LLMs supported by the router.
"""

from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.config import settings


class ModelMetadata(BaseModel):
    id: str = Field(..., description="Unique model identifier, e.g. 'ollama:llama3.2:3b'")
    name: str = Field(..., description="Human-friendly model name")
    provider: str = Field(..., description="Provider organization, e.g. 'Ollama', 'Google', 'Groq'")
    tier: str = Field(..., description="Access tier: 'Local', 'Free Tier', 'API Key'")
    badge: str = Field(..., description="Performance badge: 'Fast', 'Quality', 'Ultra-Fast', 'Reasoning'")
    description: str = Field(..., description="Model capability overview")
    context_window: str = Field(..., description="Context window size, e.g. '128k tokens'")
    is_local: bool = Field(default=False, description="Whether the model executes locally via Ollama")
    env_key: Optional[str] = Field(default=None, description="Required environment variable for API access")
    is_available: bool = Field(default=False, description="Whether this model is currently available to serve requests")
    status: str = Field(default="ready", description="Model availability status: 'ready', 'key_configured', 'key_missing'")


DEFAULT_MODEL_ID = "ollama:llama3.2:3b"

# Catalog specifications according to project architecture
MODEL_CATALOG: List[Dict] = [
    {
        "id": "ollama:llama3.2:3b",
        "name": "Llama 3.2 (3B)",
        "provider": "Ollama",
        "tier": "Local",
        "badge": "Fast",
        "is_local": True,
        "env_key": None,
        "description": "Zero-cost local 3B model running via Ollama. Low latency, private, and zero API costs.",
        "context_window": "128k tokens",
    },
    {
        "id": "ollama:llama3.1:8b",
        "name": "Llama 3.1 (8B)",
        "provider": "Ollama",
        "tier": "Local",
        "badge": "Quality",
        "is_local": True,
        "env_key": None,
        "description": "High quality local 8B model with strong reasoning, running fully offline via Ollama.",
        "context_window": "128k tokens",
    },
    {
        "id": "google:gemini-1.5-flash",
        "name": "Gemini 1.5 Flash",
        "provider": "Google",
        "tier": "Free Tier",
        "badge": "Fast",
        "is_local": False,
        "env_key": "GEMINI_API_KEY",
        "description": "Google lightweight high-speed model with generous 15 RPM free tier.",
        "context_window": "1M tokens",
    },
    {
        "id": "groq:llama-3.3-70b-versatile",
        "name": "Groq Llama 3.3 (70B)",
        "provider": "Groq",
        "tier": "Free Tier",
        "badge": "Ultra-Fast",
        "is_local": False,
        "env_key": "GROQ_API_KEY",
        "description": "Llama 3.3 70B served with ultra-low latency on Groq LPUs with free tier.",
        "context_window": "128k tokens",
    },
    {
        "id": "anthropic:claude-3-5-sonnet",
        "name": "Claude 3.5 Sonnet",
        "provider": "Anthropic",
        "tier": "API Key",
        "badge": "Reasoning",
        "is_local": False,
        "env_key": "ANTHROPIC_API_KEY",
        "description": "State-of-the-art frontier model with superior reasoning and nuanced synthesis.",
        "context_window": "200k tokens",
    },
    {
        "id": "openai:gpt-4o-mini",
        "name": "GPT-4o Mini",
        "provider": "OpenAI",
        "tier": "API Key",
        "badge": "Fast",
        "is_local": False,
        "env_key": "OPENAI_API_KEY",
        "description": "Fast and cost-effective OpenAI model for agile tasks and structuring.",
        "context_window": "128k tokens",
    },
]


def is_env_key_configured(key_name: Optional[str]) -> bool:
    """Checks whether the given environment key is configured with a non-empty string."""
    if not key_name:
        return False
    # Check specific attributes on settings
    key_mapping = {
        "GEMINI_API_KEY": settings.gemini_api_key or (settings.cloud_llm_api_key if settings.cloud_llm_provider == "gemini" else None),
        "GROQ_API_KEY": settings.groq_api_key or (settings.cloud_llm_api_key if settings.cloud_llm_provider == "groq" else None),
        "ANTHROPIC_API_KEY": settings.anthropic_api_key or (settings.cloud_llm_api_key if settings.cloud_llm_provider == "anthropic" else None),
        "OPENAI_API_KEY": settings.openai_api_key or (settings.cloud_llm_api_key if settings.cloud_llm_provider == "openai" else None),
    }
    val = key_mapping.get(key_name)
    return bool(val and val.strip())


def determine_model_status(is_local: bool, env_key: Optional[str], ollama_available: bool) -> Tuple[bool, str]:
    """Computes (is_available, status) tuple for a catalog item."""
    if is_local:
        available = ollama_available
        status_val = "ready" if ollama_available else "unreachable"
    else:
        configured = is_env_key_configured(env_key)
        available = configured
        status_val = "key_configured" if configured else "key_missing"
    return available, status_val


def get_model_metadata(model_id: str, ollama_available: bool = True) -> Optional[ModelMetadata]:
    """Retrieves metadata for a specific model ID."""
    for item in MODEL_CATALOG:
        if item["id"] == model_id:
            available, status_val = determine_model_status(
                is_local=item["is_local"],
                env_key=item["env_key"],
                ollama_available=ollama_available,
            )
            return ModelMetadata(**item, is_available=available, status=status_val)
    return None


def get_all_models(ollama_available: bool = True) -> List[ModelMetadata]:
    """Returns all models in the catalog with current availability status."""
    models: List[ModelMetadata] = []
    for item in MODEL_CATALOG:
        available, status_val = determine_model_status(
            is_local=item["is_local"],
            env_key=item["env_key"],
            ollama_available=ollama_available,
        )
        models.append(ModelMetadata(**item, is_available=available, status=status_val))
    return models
