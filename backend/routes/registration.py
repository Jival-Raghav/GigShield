"""Worker registration and profile routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_worker
from models.worker import Worker
from models.worker_location_trace import WorkerLocationTrace
from schemas.wallet import WalletTransactionResponse, WorkerWalletResponse
from schemas.worker import WorkerCreate, WorkerLocationTraceCreate, WorkerLocationTraceResponse, WorkerResponse, WorkerUpdate
from services.zone_granularity import map_coordinates_to_zone
from services import registration_service, wallet_service

router = APIRouter(tags=["Registration"])


@router.post("/workers/register", response_model=WorkerResponse, status_code=status.HTTP_201_CREATED)
def register_worker(payload: WorkerCreate, db: Session = Depends(get_db)) -> Worker:
    try:
        worker = registration_service.register_worker(payload=payload, db=db)
        db.commit()
        db.refresh(worker)
        return worker
    except ValueError as exc:
        db.rollback()
        message = str(exc)
        if "already exists" in message:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=message) from exc
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=message) from exc
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Phone number already exists") from exc


@router.get("/workers/{worker_id}", response_model=WorkerResponse, status_code=status.HTTP_200_OK)
def get_worker(
    worker_id: str,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> Worker:
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if worker is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")

    if str(worker.id) != str(current_worker.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access another worker profile")

    return worker


@router.put("/workers/{worker_id}", response_model=WorkerResponse, status_code=status.HTTP_200_OK)
def update_worker(
    worker_id: str,
    payload: WorkerUpdate,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> Worker:
    worker = db.query(Worker).filter(Worker.id == worker_id).first()
    if worker is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Worker not found")

    if str(worker.id) != str(current_worker.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot modify another worker profile")

    update_data = payload.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(worker, key, value)

    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker


@router.post("/workers/location/trace", response_model=WorkerLocationTraceResponse, status_code=status.HTTP_200_OK)
def add_location_trace(
    payload: WorkerLocationTraceCreate,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> WorkerLocationTraceResponse:
    mapped = map_coordinates_to_zone(payload.latitude, payload.longitude)

    trace = WorkerLocationTrace(
        worker_id=current_worker.id,
        latitude=float(payload.latitude),
        longitude=float(payload.longitude),
        accuracy_meters=payload.accuracy_meters,
        source=str(payload.source or "browser_periodic")[:32],
        mapped_parent_zone_id=(mapped or {}).get("parent_zone_id"),
        mapped_fine_zone_id=(mapped or {}).get("fine_zone_id"),
    )

    db.add(trace)
    db.commit()

    return WorkerLocationTraceResponse(
        mapped_parent_zone_id=trace.mapped_parent_zone_id,
        mapped_fine_zone_id=trace.mapped_fine_zone_id,
        accepted=True,
    )


@router.get("/workers/{worker_id}/wallet", response_model=WorkerWalletResponse, status_code=status.HTTP_200_OK)
def get_worker_wallet(
    worker_id: str,
    tx_limit: int = 10,
    db: Session = Depends(get_db),
    current_worker: Worker = Depends(get_current_worker),
) -> WorkerWalletResponse:
    if str(worker_id) != str(current_worker.id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot access another worker wallet")

    wallet, transactions = wallet_service.get_worker_wallet_snapshot(db=db, worker_id=current_worker.id, tx_limit=tx_limit)
    db.commit()
    db.refresh(wallet)

    return WorkerWalletResponse(
        worker_id=str(current_worker.id),
        balance=float(wallet.balance or 0.0),
        updated_at=wallet.updated_at,
        recent_transactions=[
            WalletTransactionResponse(
                id=str(item.id),
                amount=float(item.amount or 0.0),
                entry_type=item.entry_type.value,
                description=item.description,
                payout_id=str(item.payout_id) if item.payout_id else None,
                claim_id=str(item.claim_id) if item.claim_id else None,
                created_at=item.created_at,
            )
            for item in transactions
        ],
    )
