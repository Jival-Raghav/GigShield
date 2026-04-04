"""Application configuration for Raah Saathi backend."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_phone(value: str) -> str:
    compact = re.sub(r"[\s\-()]", "", value.strip())
    if compact.startswith("+"):
        normalized = "+" + re.sub(r"\D", "", compact[1:])
    else:
        normalized = re.sub(r"\D", "", compact)
    if not normalized.startswith("+"):
        normalized = "+" + normalized
    return normalized


def _parse_phone_list(value: str | None) -> tuple[str, ...]:
    if not value:
        return tuple()
    phones: list[str] = []
    for token in value.split(","):
        item = token.strip()
        if not item:
            continue
        phones.append(_normalize_phone(item))
    return tuple(sorted(set(phones)))


@dataclass(frozen=True)
class Settings:
    database_url: str = os.getenv(
        "DATABASE_URL",
        "postgresql://gigshield:gigshield123@localhost:5432/gigshield",
    )
    redis_url: str = os.getenv("REDIS_URL", "redis://localhost:6379")
    secret_key: str = os.getenv("SECRET_KEY", "your-secret-key-here")
    razorpay_key_id: str = os.getenv("RAZORPAY_KEY_ID", "mock_key_id")
    razorpay_key_secret: str = os.getenv("RAZORPAY_KEY_SECRET", "mock_key_secret")
    razorpay_fund_account: str = os.getenv("RAZORPAY_FUND_ACCOUNT", "mock_fund_account")
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = _parse_bool(os.getenv("DEBUG"), default=True)
    admin_phones: tuple[str, ...] = _parse_phone_list(os.getenv("ADMIN_PHONES"))


settings = Settings()
