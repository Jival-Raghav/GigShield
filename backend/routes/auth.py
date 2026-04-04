"""Authentication routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from database import get_db
from schemas.auth import LoginResponse, OtpRequest, OtpRequestResponse, OtpVerifyRequest
from services import auth_service

router = APIRouter(tags=["Auth"])


@router.post("/auth/otp/request", response_model=OtpRequestResponse, status_code=status.HTTP_200_OK)
def request_otp(payload: OtpRequest, db: Session = Depends(get_db)) -> OtpRequestResponse:
    try:
        data = auth_service.request_phone_otp(phone=payload.phone, db=db)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        if "digits" in message:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
        if "Too many" in message:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message) from exc
    return OtpRequestResponse(**data)


@router.post("/auth/otp/verify", response_model=LoginResponse, status_code=status.HTTP_200_OK)
def verify_otp(payload: OtpVerifyRequest, db: Session = Depends(get_db)) -> LoginResponse:
    try:
        data = auth_service.verify_phone_otp(phone=payload.phone, otp=payload.otp, db=db)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc
    except ValueError as exc:
        message = str(exc)
        if "digits" in message:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
        if "Too many" in message:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=message) from exc
    return LoginResponse(**data)
