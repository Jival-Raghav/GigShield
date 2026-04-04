"""Pydantic schemas for authentication."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class LoginRequest(BaseModel):
    phone: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    expires_at: datetime
    worker_id: UUID
    is_admin: bool


class OtpRequest(BaseModel):
    phone: str


class OtpRequestResponse(BaseModel):
    message: str
    expires_in_seconds: int
    otp_debug: str | None = None


class OtpVerifyRequest(BaseModel):
    phone: str
    otp: str
