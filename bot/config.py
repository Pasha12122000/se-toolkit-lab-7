from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


ENV_FILE = Path(__file__).resolve().parent.parent / ".env.bot.secret"


class Settings(BaseSettings):
    bot_token: str = Field(alias="BOT_TOKEN")
    lms_api_base_url: str = Field(alias="LMS_API_BASE_URL")
    lms_api_key: str = Field(alias="LMS_API_KEY")
    llm_api_model: str = Field(alias="LLM_API_MODEL")
    llm_api_key: str = Field(alias="LLM_API_KEY")
    llm_api_base_url: str = Field(alias="LLM_API_BASE_URL")

    model_config = SettingsConfigDict(
        env_file=ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )


def load_settings() -> Settings:
    return Settings()
