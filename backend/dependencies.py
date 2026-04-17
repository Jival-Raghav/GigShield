"""Shared FastAPI dependency helpers for authentication/authorization."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import ExpiredSignatureError, JWTError, jwt
from sqlalchemy.orm import Session

from config import settings
from database import get_db
from models.worker import PlatformEnum, VehicleTypeEnum, Worker

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/otp/verify")


def get_current_worker(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> Worker:
    """Decode JWT bearer token and return authenticated worker."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except ExpiredSignatureError as exc:
        raise credentials_exc from exc
    except JWTError as exc:
        raise credentials_exc from exc

    worker_sub = payload.get("sub")
    if worker_sub is None:
        raise credentials_exc

    try:
        worker_id = UUID(str(worker_sub))
    except ValueError as exc:
        raise credentials_exc from exc

    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if worker is None:
        raise credentials_exc
    return worker


def get_current_admin(worker: Worker = Depends(get_current_worker)) -> Worker:
    """Return authenticated admin worker."""
    if worker.phone in settings.admin_phones:
        return worker

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Admin access required",
    )


def get_current_admin_token(token: str = Depends(oauth2_scheme)) -> Worker:
    """Return a synthetic admin worker when the token is marked as admin."""
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired authentication token",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except ExpiredSignatureError as exc:
        raise credentials_exc from exc
    except JWTError as exc:
        raise credentials_exc from exc

    if not payload.get("is_admin"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    phone = str(payload.get("phone") or "")
    if phone not in settings.admin_phones:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")

    return Worker(
        name="Admin",
        phone=phone,
        platform=PlatformEnum.swiggy,
        vehicle_type=VehicleTypeEnum.other,
        micro_zone_id="ADMIN",
        tenure_weeks=0,
        avg_weekly_income=0.0,
        trust_score=1.0,
        cold_start=False,
    )
