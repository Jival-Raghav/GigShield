"""Payment execution services for claim payouts."""

from __future__ import annotations

import logging
import time
from datetime import datetime, timezone
from typing import Literal

import httpx
from sqlalchemy.orm import Session

from config import settings
from models.payout import PaymentStatusEnum, Payout
from models.worker import Worker
from services import wallet_service

logger = logging.getLogger(__name__)

GatewayProvider = Literal["upi_simulator", "razorpay_test", "stripe_sandbox"]


def _resolve_gateway(gateway: str | None) -> GatewayProvider:
    selected = (gateway or settings.payout_default_gateway or "upi_simulator").strip().lower()
    if selected not in {"upi_simulator", "razorpay_test", "stripe_sandbox"}:
        return "upi_simulator"
    return selected  # type: ignore[return-value]


def _complete_simulated_payout(payout: Payout, provider_reference: str) -> None:
    payout.razorpay_order_id = provider_reference
    payout.payment_status = PaymentStatusEnum.completed
    payout.completed_at = datetime.now(timezone.utc)


def _simulate_provider_payout(payout: Payout, gateway: GatewayProvider) -> None:
    if settings.payout_simulator_latency_ms > 0:
        time.sleep(min(settings.payout_simulator_latency_ms, 2000) / 1000.0)

    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    logger.warning("Using mock payout simulator for payout %s via gateway %s.", payout.id, gateway)
    if gateway == "stripe_sandbox":
        _complete_simulated_payout(payout, f"STRIPE-SBX-{stamp}")
        return
    if gateway == "razorpay_test":
        _complete_simulated_payout(payout, f"RAZORPAY-TEST-{stamp}")
        return
    _complete_simulated_payout(payout, f"UPI-SIM-{stamp}")


def _try_razorpay_test_api(payout: Payout, worker: Worker) -> bool:
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
        with httpx.Client(timeout=12.0) as client:
            response = client.post(
                "https://api.razorpay.com/v1/payouts",
                auth=(settings.razorpay_key_id, settings.razorpay_key_secret),
                json=payload,
            )
        if response.status_code in {200, 201}:
            response_data = response.json()
            payout.razorpay_order_id = response_data.get("id") or payout.razorpay_order_id
            payout.payment_status = PaymentStatusEnum.processing
            return True
    except httpx.HTTPError as exc:
        logger.warning("Razorpay test API call failed, using simulator fallback: %s", exc)
        logger.warning("Using mock payout simulator for payout %s because Razorpay test API failed.", payout.id)
    return False


def _try_stripe_sandbox_api(payout: Payout, worker: Worker) -> bool:
    if not settings.stripe_secret_key:
        return False

    payload = {
        "amount": int(float(payout.amount) * 100),
        "currency": "inr",
        "confirm": True,
        "payment_method": "pm_card_visa",
        "payment_method_types[]": "card",
        "description": f"Raah Saathi claim payout {payout.claim_id} to {worker.name}",
        "metadata[claim_id]": str(payout.claim_id),
        "metadata[worker_id]": str(worker.id),
    }

    try:
        with httpx.Client(timeout=12.0) as client:
            response = client.post(
                f"{settings.stripe_api_base.rstrip('/')}/v1/payment_intents",
                auth=(settings.stripe_secret_key, ""),
                data=payload,
            )
        if response.status_code in {200, 201}:
            response_data = response.json()
            payout.razorpay_order_id = response_data.get("id") or payout.razorpay_order_id
            status_value = str(response_data.get("status") or "succeeded").lower()
            payout.payment_status = PaymentStatusEnum.completed if status_value in {"succeeded", "processing"} else PaymentStatusEnum.processing
            if payout.payment_status == PaymentStatusEnum.completed:
                payout.completed_at = datetime.now(timezone.utc)
            return True
        logger.warning("Stripe sandbox payout failed: status=%s body=%s", response.status_code, response.text)
    except httpx.HTTPError as exc:
        logger.warning("Stripe sandbox API call failed, using simulator fallback: %s", exc)
        logger.warning("Using mock payout simulator for payout %s because Stripe sandbox API failed.", payout.id)
    return False


def initiate_gateway_payout(
    payout: Payout,
    worker: Worker,
    db: Session,
    gateway: str | None = None,
) -> Payout:
    """Initiate payout via configured gateway; simulators complete instantly for demos."""
    if not worker.upi_id:
        payout.payment_status = PaymentStatusEnum.failed
        db.add(payout)
        db.commit()
        db.refresh(payout)
        return payout

    selected_gateway = _resolve_gateway(gateway)

    if selected_gateway == "stripe_sandbox":
        if not _try_stripe_sandbox_api(payout=payout, worker=worker):
            _simulate_provider_payout(payout=payout, gateway=selected_gateway)
    elif selected_gateway == "razorpay_test":
        has_real_test_key = settings.razorpay_key_id.startswith("rzp_test_") and "mock" not in settings.razorpay_key_id.lower()
        if has_real_test_key:
            did_start = _try_razorpay_test_api(payout=payout, worker=worker)
            if not did_start:
                _simulate_provider_payout(payout=payout, gateway=selected_gateway)
        else:
            _simulate_provider_payout(payout=payout, gateway=selected_gateway)
    else:
        _simulate_provider_payout(payout=payout, gateway=selected_gateway)

    db.add(payout)
    db.flush()

    if payout.payment_status == PaymentStatusEnum.completed:
        wallet_service.credit_for_completed_payout(
            db=db,
            payout=payout,
            description=f"Payout credited via {selected_gateway}",
        )

    db.commit()
    db.refresh(payout)
    return payout


def initiate_upi_payout(payout: Payout, worker: Worker, db: Session) -> Payout:
    """Backward-compatible wrapper that routes through default gateway."""
    return initiate_gateway_payout(payout=payout, worker=worker, db=db, gateway=None)
