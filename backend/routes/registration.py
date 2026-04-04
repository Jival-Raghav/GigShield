"""Worker registration and profile routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from database import get_db
from dependencies import get_current_worker
from models.worker import Worker
from schemas.worker import WorkerCreate, WorkerResponse, WorkerUpdate
from services import registration_service

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

    update_data = payload.model_dump(exclude_none=True)
    for key, value in update_data.items():
        setattr(worker, key, value)

    db.add(worker)
    db.commit()
    db.refresh(worker)
    return worker
