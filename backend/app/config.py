import os
import secrets
from typing import List, Optional, Union
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

# Resolve default model and upload path relative to the project root
_BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PROJECT_ROOT = os.path.dirname(_BACKEND_DIR)
_BACKEND_ENV = os.path.join(_BACKEND_DIR, ".env")
_ROOT_ENV = os.path.join(_PROJECT_ROOT, ".env")
_DEFAULT_DB_FILE = os.path.join(_BACKEND_DIR, "deepguard.db").replace("\\", "/")
_DEFAULT_DATABASE_URL = f"sqlite:///{_DEFAULT_DB_FILE}"
_DEFAULT_MODEL_PATH = os.path.join(_PROJECT_ROOT, "ai", "models", "efficientnet_b0_ffpp_c23.pth")
_DEFAULT_UPLOAD_DIR = os.path.join(_BACKEND_DIR, "uploads")


class Settings(BaseSettings):
    # ── Application Environment ─────────────────────────────────────────────
    PROJECT_NAME: str = "DeepGuard AI API"
    ENVIRONMENT: str = "development"     # "development" | "staging" | "production"
    DEBUG: bool = False

    # ── Database (PostgreSQL in production, SQLite fallback for local dev) ─
    DATABASE_URL: str = _DEFAULT_DATABASE_URL
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 20
    DB_POOL_RECYCLE: int = 1800          # 30 minutes
    DB_POOL_PRE_PING: bool = True

    # ── Security & Authentication ───────────────────────────────────────────
    # RSA keys for RS256 JWT signing – loaded from env variables or fallback files
    JWT_PRIVATE_KEY: str = os.getenv("JWT_PRIVATE_KEY", "")
    JWT_PUBLIC_KEY: str = os.getenv("JWT_PUBLIC_KEY", "")
    # If keys are empty we fall back to HS256 secret (for backward compatibility)
    JWT_SECRET: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:3000"]

    # ── Storage Configuration ───────────────────────────────────────────────
    UPLOAD_STORAGE_DIR: str = _DEFAULT_UPLOAD_DIR
    MAX_UPLOAD_SIZE_MB: int = 50

    # ── AI / Inference Settings ─────────────────────────────────────────────
    AI_MODEL_PATH: str = _DEFAULT_MODEL_PATH
    AI_INFERENCE_TIMEOUT: int = 30       # seconds
    AI_DEVICE: str = "auto"              # "auto" | "cpu" | "cuda"
    AI_MODEL_NAME: str = "EfficientNet-B0"

    # ── Email / SMTP Configuration ──────────────────────────────────────────
    # Gmail: use SMTP_HOST=smtp.gmail.com, SMTP_PORT=587 (or 465 for SSL)
    # Requires an App Password (not your main Gmail password).
    # Generate at: https://myaccount.google.com/apppasswords
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""         # Gmail address, e.g. yourname@gmail.com
    SMTP_PASSWORD: str = ""     # Gmail App Password (16-char, spaces removed)
    MAIL_FROM_NAME: str = "DeepGuard AI"

    @field_validator("SMTP_USER", mode="before")
    @classmethod
    def parse_smtp_user(cls, v: Optional[str]) -> str:
        if not v:
            v = os.getenv("SMTP_USERNAME") or os.getenv("MAIL_USERNAME") or ""
        return str(v).strip().strip("'\"")

    @field_validator("SMTP_PASSWORD", mode="before")
    @classmethod
    def parse_smtp_password(cls, v: Optional[str]) -> str:
        if not v:
            v = os.getenv("SMTP_PASS") or os.getenv("MAIL_PASSWORD") or ""
        return str(v).replace(" ", "").strip().strip("'\"")

    @field_validator("SMTP_HOST", mode="before")
    @classmethod
    def parse_smtp_host(cls, v: Optional[str]) -> str:
        if not v:
            v = os.getenv("MAIL_SERVER") or "smtp.gmail.com"
        return str(v).strip().strip("'\"")

    @field_validator("SMTP_PORT", mode="before")
    @classmethod
    def parse_smtp_port(cls, v: Union[str, int, None]) -> int:
        if v is None or v == "":
            v = os.getenv("MAIL_PORT") or 587
        return int(v)

    @field_validator("MAIL_FROM_NAME", mode="before")
    @classmethod
    def parse_mail_from_name(cls, v: Optional[str]) -> str:
        if not v:
            v = os.getenv("SMTP_FROM_NAME") or os.getenv("SMTP_FROM") or "DeepGuard AI"
        return str(v).strip().strip("'\"")

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.strip().startswith("[") and v.strip().endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    model_config = SettingsConfigDict(
        env_file=(_BACKEND_ENV, _ROOT_ENV, ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()
