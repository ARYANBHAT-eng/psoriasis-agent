from typing import Annotated
from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _parse_allowed_origins(raw: str) -> list[str]:
    value = (raw or "").strip()
    origins = [o.strip() for o in value.split(",") if o.strip()]
    if "*" in origins:
        raise ValueError("ALLOWED_ORIGINS must be explicit domains; '*' is not allowed")
    if not origins:
        raise ValueError("ALLOWED_ORIGINS must contain at least one origin")
    return origins


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"
    port: int = 8000
    database_url: str = "sqlite:///./psoriasis.db"
    secret_key: str = ""
    access_token_expire_days: int = 7
    allowed_origins: str = "http://localhost:8501"

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def validate_origins(cls, v: str) -> str:
        _parse_allowed_origins(v)
        return v

    def get_allowed_origins(self) -> list[str]:
        return _parse_allowed_origins(self.allowed_origins)

    @model_validator(mode="after")
    def validate_production(self) -> "Settings":
        if self.app_env != "production":
            return self
        if "sqlite" in self.database_url.lower():
            raise ValueError(
                "DATABASE_URL must not use SQLite in production. "
                "Set DATABASE_URL to a PostgreSQL connection string."
            )
        if not self.secret_key or self.secret_key in ("changeme", "secret", "dev", ""):
            raise ValueError(
                "SECRET_KEY must be set to a strong random value in production. "
                "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        return self


settings = Settings()


def get_settings() -> Settings:
    return settings
