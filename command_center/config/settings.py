from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    # ADK / Gemini
    GOOGLE_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.0-flash"

    # OAuth for Google APIs
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    CALENDAR_REFRESH_TOKEN: str = ""
    GMAIL_REFRESH_TOKEN: str = ""

    # Search
    SEARCH_API_KEY: str = ""
    SEARCH_API_URL: str = "https://customsearch.googleapis.com/customsearch/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://user:pass@localhost:5432/db"

    # API
    ALLOWED_ORIGINS: List[str] = ["*"]
    API_KEY_HEADER: str = "X-API-Key"

    # Thresholds
    AMBIGUITY_THRESHOLD: float = 0.6
    TOOL_TIMEOUT_MS: int = 10000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
