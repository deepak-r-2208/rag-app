"""Application settings, loaded from environment variables (.env in local dev).

Nothing here requires a paid service: DATABASE_URL points at a local
Postgres (e.g. the docker-compose `db` service), and OLLAMA_BASE_URL points
at a local Ollama instance. No API keys required anywhere.
"""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Local Postgres connection string. In docker-compose this is overridden
    # to point at the `db` service; for non-Docker local dev it defaults to
    # a Postgres running on your own machine.
    database_url: str = "postgresql://ragnify:ragnify@localhost:5432/ragnify"

    # Secret used to sign our own login tokens. Generate one with:
    #   openssl rand -hex 32
    # and put it in backend/.env — don't use the placeholder in production.
    jwt_secret: str = "change-this-to-a-random-string-openssl-rand-hex-32"
    jwt_expiry_hours: int = 24 * 7

    # Local Ollama instance. In docker-compose this is overridden to
    # http://ollama:11434 (the service name); for non-Docker local dev it
    # defaults to Ollama running on your own machine.
    ollama_base_url: str = "http://localhost:11434"
    ollama_chat_model: str = "llama3.1:8b"

    # Comma-separated list of origins allowed to call this API.
    cors_origins: str = "http://localhost:5173"

    # Retrieval tuning.
    top_k: int = 5
    min_relevance_score: float = 0.08

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
