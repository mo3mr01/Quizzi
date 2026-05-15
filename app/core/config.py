import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import field_validator

logger = logging.getLogger("quiz_api")


class Settings(BaseSettings):
    groq_api_key: str = ""
    supabase_url: str = ""
    supabase_key: str = ""
    supabase_service_key: str = ""
    app_name: str = "Quiz App API"
    app_version: str = "0.1.0"
    debug: bool = False
    environment: str = "production"
    admin_email: str = ""
    cors_origins: str = "*"
    max_upload_size_mb: int = 10
    max_questions: int = 20
    daily_quiz_limit: int = 5
    groq_timeout_seconds: int = 30
    groq_max_retries: int = 2

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v.lower() not in allowed:
            raise ValueError(f"environment must be one of {allowed}, got '{v}'")
        return v.lower()

    @field_validator("max_upload_size_mb")
    @classmethod
    def validate_upload_size(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError(f"max_upload_size_mb must be between 1 and 100, got {v}")
        return v

    @field_validator("max_questions")
    @classmethod
    def validate_max_questions(cls, v: int) -> int:
        if v < 1 or v > 50:
            raise ValueError(f"max_questions must be between 1 and 50, got {v}")
        return v

    @field_validator("daily_quiz_limit")
    @classmethod
    def validate_daily_limit(cls, v: int) -> int:
        if v < 1 or v > 100:
            raise ValueError(f"daily_quiz_limit must be between 1 and 100, got {v}")
        return v

    @field_validator("groq_timeout_seconds")
    @classmethod
    def validate_groq_timeout(cls, v: int) -> int:
        if v < 5 or v > 120:
            raise ValueError(f"groq_timeout_seconds must be between 5 and 120, got {v}")
        return v

    @field_validator("groq_max_retries")
    @classmethod
    def validate_retries(cls, v: int) -> int:
        if v < 0 or v > 5:
            raise ValueError(f"groq_max_retries must be between 0 and 5, got {v}")
        return v

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_size_mb * 1024 * 1024

    def validate_required(self) -> None:
        required = {
            "GROQ_API_KEY": self.groq_api_key,
            "SUPABASE_URL": self.supabase_url,
            "SUPABASE_KEY": self.supabase_key,
            "SUPABASE_SERVICE_KEY": self.supabase_service_key,
        }
        missing = [name for name, val in required.items() if not val]
        if missing:
            raise RuntimeError(
                f"Missing required environment variables: {', '.join(missing)}"
            )


settings = Settings()
