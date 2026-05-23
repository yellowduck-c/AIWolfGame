from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

ENV_FILE = Path(__file__).resolve().parents[1] / ".env"


class Settings(BaseSettings):
    # app
    app_name: str = Field(default="AI Werewolf Backend")
    app_env: str = Field(default="development")
    app_host: str = Field(default="127.0.0.1")
    app_port: int = Field(default=8000)

    # logging
    log_level: str = Field(default="INFO")

    # mysql
    mysql_host: str = Field(default="127.0.0.1")
    mysql_port: int = Field(default=3306)
    mysql_user: str = Field(default="root")
    mysql_password: str = Field(default="password")
    mysql_database: str = Field(default="ai_werewolf")

    # redis
    redis_host: str = Field(default="127.0.0.1")
    redis_port: int = Field(default=6379)
    redis_password: str = Field(default="")
    redis_db: int = Field(default=0)
    redis_prefix: str = Field(default="ai_werewolf")

    # llm
    llm_provider: str = Field(default="mock")
    llm_model: str = Field(default="gpt-4o-mini")
    llm_api_key: str = Field(default="")
    llm_base_url: str = Field(default="")
    llm_temperature: float = Field(default=0.7)
    llm_timeout_seconds: int = Field(default=30)
    llm_max_retries: int = Field(default=1)

    model_config = SettingsConfigDict(env_file=ENV_FILE, env_file_encoding="utf-8", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
