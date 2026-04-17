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

    # Compatibility: support engines that return trust_adjustment instead of trust_discount.
    if "trust_discount" not in quote:
        quote["trust_discount"] = float(quote.get("trust_adjustment", 1.0))

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

    if str(current_worker.id) != str(payload.worker_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot create policy for another worker")

    try:
        quote = premium_engine.calculate_premium(worker=worker, coverage_tier=payload.coverage_tier.value, db=db)
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(exc)) from exc

    trust_discount = float(quote.get("trust_discount", quote.get("trust_adjustment", 1.0)))
    today = date.today()

    # Enforce max one active policy per worker by deactivating older active policies first.
    existing_active = (
        db.query(Policy)
        .filter(Policy.worker_id == payload.worker_id, Policy.is_active.is_(True))
        .all()
    )
    for prev_policy in existing_active:
        prev_policy.is_active = False
        if prev_policy.valid_to > today:
            prev_policy.valid_to = today

    policy = Policy(
        worker_id=payload.worker_id,
        coverage_tier=payload.coverage_tier,
        coverage_ratio=quote["coverage_ratio"],
        max_weekly_coverage=quote["max_weekly_coverage"],
        weekly_premium=quote["weekly_premium"],
        risk_multiplier=quote["risk_multiplier"],
        trust_discount=trust_discount,
        is_active=True,
        valid_from=today,
        valid_to=today + timedelta(days=7),
    )
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.delete("/policies/{policy_id}", response_model=PolicyResponse, status_code=status.HTTP_200_OK)
def deactivate_policy(
    policy_id: str,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> Policy:
    policy = db.query(Policy).filter(Policy.id == policy_id).first()
    if policy is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Policy not found")

    if str(policy.worker_id) != str(current_worker.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify another worker policy")

    if policy.is_active:
        policy.is_active = False
        today = date.today()
        if policy.valid_to > today:
            policy.valid_to = today
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
