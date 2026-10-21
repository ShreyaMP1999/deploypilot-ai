from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./deploypilot.db"
    jwt_secret: str = Field(min_length=32)
    demo_password: str = Field(min_length=12)
    cors_origins: str = "http://localhost:3000"
    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    agent_mode: str = "offline"
    # Operator-supplied rates, never assumed to be current vendor pricing.
    input_cost_per_million: float = 0
    output_cost_per_million: float = 0
    token_ttl_minutes: int = 60


@lru_cache
def settings():
    return Settings()
