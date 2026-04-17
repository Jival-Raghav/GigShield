"""Mock wallet service for crediting completed payouts."""

from __future__ import annotations

from sqlalchemy.orm import Session

from models.payout import PaymentStatusEnum, Payout
from models.wallet import WalletEntryTypeEnum, WalletTransaction, WorkerWallet


def get_or_create_wallet(*, db: Session, worker_id) -> WorkerWallet:
    wallet = db.query(WorkerWallet).filter(WorkerWallet.worker_id == worker_id).first()
    if wallet is not None:
        return wallet

    wallet = WorkerWallet(worker_id=worker_id, balance=0.0)
    db.add(wallet)
    db.flush()
    return wallet


def credit_for_completed_payout(*, db: Session, payout: Payout, description: str | None = None) -> WalletTransaction | None:
    if payout.payment_status != PaymentStatusEnum.completed:
        return None
    if float(payout.amount or 0.0) <= 0.0:
        return None

    existing = db.query(WalletTransaction).filter(WalletTransaction.payout_id == payout.id).first()
    if existing is not None:
        return existing

    wallet = get_or_create_wallet(db=db, worker_id=payout.worker_id)
    wallet.balance = round(float(wallet.balance or 0.0) + float(payout.amount or 0.0), 2)

    tx = WalletTransaction(
        wallet_id=wallet.id,
        worker_id=payout.worker_id,
        payout_id=payout.id,
        claim_id=payout.claim_id,
        entry_type=WalletEntryTypeEnum.credit,
        amount=float(payout.amount or 0.0),
        description=description or "Claim payout credited",
    )
    db.add(wallet)
    db.add(tx)
    return tx


def get_worker_wallet_snapshot(*, db: Session, worker_id, tx_limit: int = 10) -> tuple[WorkerWallet, list[WalletTransaction]]:
    wallet = get_or_create_wallet(db=db, worker_id=worker_id)
    safe_limit = max(1, min(tx_limit, 50))
    transactions = (
        db.query(WalletTransaction)
        .filter(WalletTransaction.worker_id == worker_id)
        .order_by(WalletTransaction.created_at.desc())
        .limit(safe_limit)
        .all()
    )
    return wallet, transactions
