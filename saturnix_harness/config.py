from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration layer for SATURNIX-HARNESS.

    Every external brain and subsystem is configured through environment variables
    so the same code path works for local development, Docker, CI, and production.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    saturnix_env: Literal["development", "test", "production"] = "development"
    saturnix_log_level: str = "INFO"
    saturnix_api_host: str = "0.0.0.0"
    saturnix_api_port: int = 8088
    saturnix_enable_mock_brains: bool = True
    saturnix_enable_ollama: bool = False
    saturnix_default_brain: str = "openai"
    saturnix_local_only: bool = False
    saturnix_enable_agents_sdk: bool = True
    saturnix_agents_session_path: Path = Field(default=Path("./data/agents_sessions.sqlite3"))
    saturnix_agents_trace_namespace: str = "sdk:traces"

    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4.1"
    openai_agents_model: str = "gpt-4.1-mini"

    anthropic_api_key: SecretStr | None = None
    claude_model: str = "claude-3-7-sonnet-latest"

    google_api_key: SecretStr | None = None
    gemini_model: str = "gemini-2.0-flash"

    ollama_base_url: str = "http://localhost:11434"
    ollama_gemma_model: str = "gemma3"
    ollama_coding_model: str = "deepseek-coder-v2"
    ollama_minimax_model: str = "minimax"
    ollama_qwen_coder_model: str = "qwen2.5-coder"
    ollama_deepseek_coder_model: str = "deepseek-coder-v2"
    ollama_request_timeout: int = 120

    groq_api_key: SecretStr | None = None
    groq_chat_model: str = "llama-3.3-70b-versatile"
    groq_transcription_model: str = "whisper-large-v3-turbo"
    groq_tts_model: str = "canopylabs/orpheus-v1-english"
    groq_tts_voice: str = "troy"
    groq_tts_response_format: str = "wav"

    saturnix_sqlite_path: Path = Field(default=Path("./data/saturnix.sqlite3"))
    saturnix_chroma_path: Path = Field(default=Path("./data/chroma"))
    saturnix_enable_chroma: bool = True

    saturnix_dashboard_auth_required: bool = False
    saturnix_jwt_secret: SecretStr | None = None
    saturnix_dashboard_encryption_key: SecretStr | None = None
    saturnix_cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"
    saturnix_rate_limit_per_minute: int = 120
    saturnix_lockdown_mode: bool = False
    saturnix_allowed_storage_roots: str = "./data,./backups"

    n8n_webhook_url: str | None = None

    @property
    def is_production(self) -> bool:
        return self.saturnix_env == "production"

    @property
    def sqlite_path(self) -> Path:
        return self.saturnix_sqlite_path

    @property
    def chroma_path(self) -> Path:
        return self.saturnix_chroma_path

    @staticmethod
    def has_secret(value: SecretStr | None) -> bool:
        return bool(value and value.get_secret_value().strip())


@lru_cache
def get_settings() -> Settings:
    return Settings()
