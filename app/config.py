"""Application configuration helpers."""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Settings(BaseSettings):
    """Configuration sourced from environment variables / .env."""

    groq_api_key: str = Field(..., alias="GROQ_API_KEY")
    groq_model: str = Field(
        default="llama-3.1-8b-instant", alias="GROQ_MODEL", description="Groq model"
    )
    groq_temperature: float = Field(
        default=0.2, alias="GROQ_TEMPERATURE", description="Sampling temperature"
    )
    groq_max_tokens: int = Field(
        default=800,
        alias="GROQ_MAX_TOKENS",
        description="Upper bound for tokens each agent can emit",
    )

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def ensure_environment(self) -> None:
        """Ensure downstream SDKs see the Groq token."""
        if "GROQ_API_KEY" not in os.environ:
            os.environ["GROQ_API_KEY"] = self.groq_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings instance."""
    settings = Settings()
    settings.ensure_environment()
    return settings
