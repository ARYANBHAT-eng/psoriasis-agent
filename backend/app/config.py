import os
from dataclasses import dataclass


def _parse_allowed_origins(raw: str) -> list[str]:
    value = (raw or "").strip()
    origins = [origin.strip() for origin in value.split(",") if origin.strip()]
    if "*" in origins:
        raise ValueError("ALLOWED_ORIGINS must be explicit domains; '*' is not allowed")
    if not origins:
        raise ValueError("ALLOWED_ORIGINS must contain at least one origin")
    return origins


@dataclass(frozen=True)
class Settings:
    app_env: str
    port: int
    database_url: str
    allowed_origins: list[str]

    @property
    def db_url_configured(self) -> bool:
        return bool(self.database_url.strip())


def get_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "production").strip() or "production",
        port=int(os.getenv("PORT", "8000")),
        database_url=os.getenv("DATABASE_URL", "sqlite:///./psoriasis.db"),
        allowed_origins=_parse_allowed_origins(
            os.getenv("ALLOWED_ORIGINS", "http://localhost:8501")
        ),
    )
