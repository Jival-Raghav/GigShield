"""Premium quote and policy routes."""

from __future__ import annotations

from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_worker
from models.policy import Policy
from models.worker import Worker
from schemas.policy import PolicyCreate, PolicyResponse, PremiumQuoteRequest, PremiumQuoteResponse
from schemas.worker_income import BaselineIncomeResponse
from services import baseline_engine, premium_engine

router = APIRouter(tags=["Premium"])


@router.post("/baseline/compute/{worker_id}", response_model=BaselineIncomeResponse, status_code=status.HTTP_200_OK)
def compute_baseline_income(
    worker_id: str,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> BaselineIncomeResponse:
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if worker is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")

    try:
        result = baseline_engine.compute_baseline_income(worker=worker, db=db)
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return BaselineIncomeResponse(**result)


@router.post("/premium/quote", response_model=PremiumQuoteResponse, status_code=status.HTTP_200_OK)
def premium_quote(
    payload: PremiumQuoteRequest,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> PremiumQuoteResponse:
    worker = db.query(Worker).filter(Worker.id == payload.worker_id).first()
    if worker is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")

    try:
        quote = premium_engine.calculate_premium(worker=worker, coverage_tier=payload.coverage_tier.value, db=db)
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    return PremiumQuoteResponse(**quote)


@router.post("/policies/create", response_model=PolicyResponse, status_code=status.HTTP_201_CREATED)
def create_policy(
    payload: PolicyCreate,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> Policy:
    worker = db.query(Worker).filter(Worker.id == payload.worker_id).first()
    if worker is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")

    try:
        quote = premium_engine.calculate_premium(worker=worker, coverage_tier=payload.coverage_tier.value, db=db)
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    policy = Policy(
        worker_id=payload.worker_id,
        coverage_tier=payload.coverage_tier,
        coverage_ratio=quote["coverage_ratio"],
        max_weekly_coverage=quote["max_weekly_coverage"],
        weekly_premium=quote["weekly_premium"],
        risk_multiplier=quote["risk_multiplier"],
        trust_discount=quote["trust_discount"],
        is_active=True,
        valid_from=date.today(),
        valid_to=date.today() + timedelta(days=7),
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.get("/policies/{worker_id}", response_model=list[PolicyResponse], status_code=status.HTTP_200_OK)
def list_worker_policies(
    worker_id: str,
    active_only: bool = Query(default=True),
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> list[Policy]:
    query = db.query(Policy).filter(Policy.worker_id == worker_id)
    if active_only:
        query = query.filter(Policy.is_active.is_(True))

    return query.order_by(Policy.created_at.desc()).all()
