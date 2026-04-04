"""Authentication service functions."""

from __future__ import annotations

import hashlib
import secrets
import re
from datetime import datetime, timedelta, timezone

import redis
from jose import jwt
from sqlalchemy.orm import Session

from config import settings
from models.worker import Worker

JWT_ALGORITHM = "HS256"
ACCESS_TOKEN_MINUTES = 60
OTP_TTL_SECONDS = 300
OTP_REQUEST_WINDOW_SECONDS = 300
OTP_MAX_REQUESTS_PER_WINDOW = 3
OTP_MAX_VERIFY_ATTEMPTS = 5


def _otp_hash(phone: str, otp: str) -> str:
    return hashlib.sha256(f"{phone}:{otp}".encode("utf-8")).hexdigest()


def _redis_client() -> redis.Redis:
    client = redis.Redis.from_url(settings.redis_url, decode_responses=True)
    client.ping()
    return client


def _normalize_phone(phone: str) -> str:
    compact = re.sub(r"[\s\-()]", "", phone.strip())
    if compact.startswith("+"):
        normalized = "+" + re.sub(r"\D", "", compact[1:])
    else:
        normalized = re.sub(r"\D", "", compact)

    if not normalized.startswith("+"):
        normalized = "+" + normalized

    digits_count = len(normalized) - 1
    if digits_count < 10 or digits_count > 15:
        raise ValueError("Phone number must contain 10 to 15 digits")

    return normalized


def _issue_login_token(worker: Worker) -> dict:
    now = datetime.now(timezone.utc)
    expires_at = now + timedelta(minutes=ACCESS_TOKEN_MINUTES)
    is_admin = worker.phone in settings.admin_phones
    payload = {
        "sub": str(worker.id),
        "phone": worker.phone,
        "is_admin": is_admin,
        "iat": int(now.timestamp()),
        "exp": int(expires_at.timestamp()),
    }
    token = jwt.encode(payload, settings.secret_key, algorithm=JWT_ALGORITHM)

    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_at": expires_at,
        "worker_id": worker.id,
        "is_admin": is_admin,
    }


def request_phone_otp(phone: str, db: Session) -> dict:
    normalized_phone = _normalize_phone(phone)
    worker = db.query(Worker).filter(Worker.phone == normalized_phone).first()
    if worker is None:
        raise ValueError("Invalid credentials")

    try:
        client = _redis_client()
    except redis.RedisError as exc:
        raise RuntimeError("OTP service unavailable") from exc

    request_counter_key = f"otp:req:{normalized_phone}"
    current_count = client.incr(request_counter_key)
    if current_count == 1:
        client.expire(request_counter_key, OTP_REQUEST_WINDOW_SECONDS)
    if current_count > OTP_MAX_REQUESTS_PER_WINDOW:
        raise ValueError("Too many OTP requests. Please wait and retry")

    otp = f"{secrets.randbelow(1000000):06d}"
    otp_key = f"otp:code:{normalized_phone}"
    attempts_key = f"otp:attempts:{normalized_phone}"
    client.setex(otp_key, OTP_TTL_SECONDS, _otp_hash(normalized_phone, otp))
    client.setex(attempts_key, OTP_TTL_SECONDS, "0")

    # Mock delivery for local development.
    print(f"[OTP-MOCK] phone={normalized_phone} otp={otp} valid_for={OTP_TTL_SECONDS}s")

    return {
        "message": "OTP sent successfully",
        "expires_in_seconds": OTP_TTL_SECONDS,
        "otp_debug": otp if settings.debug else None,
    }


def verify_phone_otp(phone: str, otp: str, db: Session) -> dict:
    normalized_phone = _normalize_phone(phone)
    worker = db.query(Worker).filter(Worker.phone == normalized_phone).first()
    if worker is None:
        raise ValueError("Invalid credentials")

    otp_candidate = otp.strip()
    if not otp_candidate.isdigit() or len(otp_candidate) != 6:
        raise ValueError("OTP must be a 6-digit code")

    try:
        client = _redis_client()
    except redis.RedisError as exc:
        raise RuntimeError("OTP service unavailable") from exc

    otp_key = f"otp:code:{normalized_phone}"
    attempts_key = f"otp:attempts:{normalized_phone}"
    stored_hash = client.get(otp_key)
    if stored_hash is None:
        raise ValueError("OTP expired or not requested")

    attempts = client.incr(attempts_key)
    if attempts == 1:
        client.expire(attempts_key, OTP_TTL_SECONDS)
    if attempts > OTP_MAX_VERIFY_ATTEMPTS:
        client.delete(otp_key)
        client.delete(attempts_key)
        raise ValueError("Too many invalid attempts. Request a new OTP")

    if stored_hash != _otp_hash(normalized_phone, otp_candidate):
        raise ValueError("Invalid OTP")

    client.delete(otp_key)
    client.delete(attempts_key)
    return _issue_login_token(worker)


def login_with_phone(phone: str, db: Session) -> dict:
    normalized_phone = _normalize_phone(phone)
    worker = db.query(Worker).filter(Worker.phone == normalized_phone).first()
    if worker is None:
        raise ValueError("Invalid credentials")
    return _issue_login_token(worker)
