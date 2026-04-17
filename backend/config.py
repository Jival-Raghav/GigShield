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
    stripe_secret_key: str | None = os.getenv("STRIPE_SECRET_KEY")
    stripe_api_base: str = os.getenv("STRIPE_API_BASE", "https://api.stripe.com")
    payout_default_gateway: str = os.getenv("PAYOUT_DEFAULT_GATEWAY", "upi_simulator")
    payout_simulator_latency_ms: int = int(os.getenv("PAYOUT_SIMULATOR_LATENCY_MS", "0"))
    environment: str = os.getenv("ENVIRONMENT", "development")
    debug: bool = _parse_bool(os.getenv("DEBUG"), default=True)
    admin_phones: tuple[str, ...] = _parse_phone_list(os.getenv("ADMIN_PHONES"))
    traffic_provider: str = os.getenv("TRAFFIC_PROVIDER", "auto").strip().lower()
    traffic_api_base: str = os.getenv("TRAFFIC_API_BASE", "").strip()
    tomtom_traffic_api_key: str | None = os.getenv("TOMTOM_TRAFFIC_API_KEY")
    tomtom_traffic_base_url: str = os.getenv("TOMTOM_TRAFFIC_BASE_URL", "https://api.tomtom.com/traffic/services/4")
    here_traffic_api_key: str | None = os.getenv("HERE_TRAFFIC_API_KEY")
    here_traffic_base_url: str = os.getenv("HERE_TRAFFIC_BASE_URL", "https://router.hereapi.com/v8")
    google_routes_api_key: str | None = os.getenv("GOOGLE_ROUTES_API_KEY")
    google_routes_base_url: str = os.getenv("GOOGLE_ROUTES_BASE_URL", "https://routes.googleapis.com/directions/v2")
    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    news_llm_enabled: bool = _parse_bool(os.getenv("NEWS_LLM_ENABLED"), default=False)
    news_llm_api_key: str | None = os.getenv("NEWS_LLM_API_KEY") or os.getenv("GROQ_API_KEY")
    news_llm_model: str = os.getenv("NEWS_LLM_MODEL", "llama-3.1-8b-instant")
    news_llm_endpoint: str = os.getenv("NEWS_LLM_ENDPOINT", "https://api.groq.com/openai/v1/chat/completions")
    fraud_llm_enabled: bool = _parse_bool(os.getenv("FRAUD_LLM_ENABLED"), default=False)
    fraud_llm_api_key: str | None = os.getenv("FRAUD_LLM_API_KEY") or os.getenv("GROQ_API_KEY")
    fraud_llm_model: str = os.getenv("FRAUD_LLM_MODEL", "llama-3.1-8b-instant")
    fraud_llm_endpoint: str = os.getenv("FRAUD_LLM_ENDPOINT", "https://api.groq.com/openai/v1/chat/completions")
    risk_forecast_model_family: str = os.getenv("RISK_FORECAST_MODEL_FAMILY", "auto").strip().lower()
    fraud_anomaly_model_backend: str = os.getenv("FRAUD_ANOMALY_MODEL_BACKEND", "isolation_forest").strip().lower()
    waqi_api_token: str = os.getenv("WAQI_API_TOKEN", "")
    otp_ttl_seconds: int = int(os.getenv("OTP_TTL_SECONDS", "300"))
    otp_request_window_seconds: int = int(os.getenv("OTP_REQUEST_WINDOW_SECONDS", "300"))
    otp_max_requests_per_window: int = int(os.getenv("OTP_MAX_REQUESTS_PER_WINDOW", "3"))
    otp_max_verify_attempts: int = int(os.getenv("OTP_MAX_VERIFY_ATTEMPTS", "5"))
    otp_disable_rate_limit: bool = _parse_bool(os.getenv("OTP_DISABLE_RATE_LIMIT"), default=False)
    admin_forecast_mode: str = os.getenv("ADMIN_FORECAST_MODE", "hybrid")
    admin_forecast_ml_timeout_seconds: float = float(os.getenv("ADMIN_FORECAST_ML_TIMEOUT_SECONDS", "1.5"))


settings = Settings()
    