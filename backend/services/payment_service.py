"""Payment execution services for claim payouts."""

from __future__ import annotations

import logging

import httpx
from sqlalchemy.orm import Session

from config import settings
from models.payout import PaymentStatusEnum, Payout
from models.worker import Worker

logger = logging.getLogger(__name__)


def initiate_upi_payout(payout: Payout, worker: Worker, db: Session) -> Payout:
    """Initiate a UPI payout through Razorpay Payouts API.

    On success payout status is moved to processing.
    On failure payout status is moved to failed.
    """
    if not worker.upi_id:
        payout.payment_status = PaymentStatusEnum.failed
        db.add(payout)
        db.commit()
        db.refresh(payout)
        return payout

    payload = {
        "account_number": settings.razorpay_fund_account,
        "fund_account": {
            "account_type": "vpa",
            "vpa": {"address": worker.upi_id},
        },
        "amount": int(float(payout.amount) * 100),
        "currency": "INR",
        "mode": "UPI",
        "purpose": "payout",
        "narration": f"Raah Saathi claim payout {payout.claim_id}",
    }

    try:
        with httpx.Client(timeout=20.0) as client:
            response = client.post(
                "https://api.razorpay.com/v1/payouts",
                auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
                json=payload,
            )

        if response.status_code == 200:
            response_data = response.json()
            payout.razorpay_order_id = response_data.get("id")
            payout.payment_status = PaymentStatusEnum.processing
        else:
            logger.error("Razorpay payout failed: status=%s body=%s", response.status_code, response.text)
            payout.payment_status = PaymentStatusEnum.failed
    except httpx.HTTPError as exc:
        logger.exception("Razorpay payout HTTP error: %s", exc)
        payout.payment_status = PaymentStatusEnum.failed

    db.add(payout)
    db.commit()
    db.refresh(payout)
    return payout
