from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # Anthropic API
    ANTHROPIC_API_KEY: Optional[str] = None

    # Google Gemini API (기존 호환)
    GEMINI_API_KEY: Optional[str] = None

    # ElevenLabs API
    ELEVENLABS_API_KEY: Optional[str] = None

    # Pexels API
    PEXELS_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
