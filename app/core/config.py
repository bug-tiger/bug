from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """애플리케이션 설정"""

    # Anthropic API
    ANTHROPIC_API_KEY: Optional[str] = None

    # Leonardo AI API
    LEONARDO_API_KEY: Optional[str] = None
    LEONARDO_MODEL_ID: Optional[str] = "1e60896f-3c26-4296-8ecc-53e2afecc132"

    # Google Gemini API (기존 호환)
    GEMINI_API_KEY: Optional[str] = None

    # ElevenLabs API
    ELEVENLABS_API_KEY: Optional[str] = None
    ELEVENLABS_VOICE_ID: Optional[str] = "pFZP5JQG7iQjIQuC4Bku"

    # Pexels API
    PEXELS_API_KEY: Optional[str] = None

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"  # 정의되지 않은 환경변수 무시


settings = Settings()
