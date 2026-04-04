"""Background scheduler jobs for trigger polling and premium recalculation."""

from __future__ import annotations

import logging
from collections import defaultdict
from datetime import datetime, timedelta, timezone

from apscheduler.executors.asyncio import AsyncIOExecutor
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from database import SessionLocal
from models.disruption import Disruption
from models.policy import Policy
from models.payout import PaymentMethodEnum, PaymentStatusEnum, Payout
from models.claim import Claim, ClaimStatusEnum
from models.worker import Worker
from services import premium_engine, trigger_monitor

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(executors={"default": AsyncIOExecutor()}, timezone=timezone.utc)


def _previous_week_range(now: datetime) -> tuple[datetime, datetime]:
    current_week_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=now.weekday())
    previous_week_start = current_week_start - timedelta(days=7)
    return previous_week_start, current_week_start


def _current_week_range(now: datetime) -> tuple[datetime, datetime]:
    current_week_start = now.replace(hour=0, minute=0, second=0, microsecond=0) - timedelta(days=now.weekday())
    return current_week_start, now


async def poll_all_zones() -> None:
    """Poll all active zones and create disruptions/claims for newly triggered events."""
    db: Session = SessionLocal()
    try:
        zone_rows = db.query(Worker.micro_zone_id).distinct().all()
        zone_ids = [row[0] for row in zone_rows if row[0]]

        for zone_id in zone_ids:
            disruptions = await trigger_monitor.check_all_triggers(zone_id=zone_id, db=db)
            for item in disruptions:
                existing = (
                    db.query(Disruption)
                    .filter(
                        Disruption.zone_id == item["zone_id"],
                        Disruption.disruption_type == item["disruption_type"],
                        Disruption.ended_at.is_(None),
                    )
                    .first()
                )
                if existing is not None:
                    continue

                disruption = Disruption(
                    zone_id=item["zone_id"],
                    disruption_type=item["disruption_type"],
                    severity=item["severity"],
                    signal_source=item["signal_source"],
                    is_confirmed=True,
                    is_catastrophic=item.get("is_catastrophic", False),
                    started_at=item.get("started_at") or datetime.now(timezone.utc),
                    ended_at=item.get("ended_at"),
                )
                db.add(disruption)
                db.commit()
                db.refresh(disruption)
                await trigger_monitor.auto_initiate_claims(disruption=disruption, db=db)
    except Exception:
        logger.exception("Scheduler poll_all_zones failed")
    finally:
        db.close()


async def recalculate_weekly_premiums() -> None:
    """Recalculate weekly premiums for workers with active policies."""
    db: Session = SessionLocal()
    try:
        rows = (
            db.query(Policy, Worker)
            .join(Worker, Worker.id == Policy.worker_id)
            .filter(Policy.is_active.is_(True))
            .all()
        )

        pending_updates = 0
        for policy, worker in rows:
            quote = premium_engine.calculate_premium(worker=worker, coverage_tier=policy.coverage_tier.value, db=db)
            policy.weekly_premium = float(quote["weekly_premium"])
            policy.risk_multiplier = float(quote["risk_multiplier"])
            policy.trust_discount = float(quote["trust_discount"])
            db.add(policy)
            pending_updates += 1

            if pending_updates >= 50:
                db.commit()
                pending_updates = 0

        if pending_updates > 0:
            db.commit()
    except Exception:
        logger.exception("Scheduler recalculate_weekly_premiums failed")
    finally:
        db.close()


def run_weekly_settlement_now(mode: str = "previous_week") -> dict:
    """Settle approved claims and auto-complete payouts for a selected week window."""
    db: Session = SessionLocal()
    now = datetime.now(timezone.utc)
    if mode == "current_week":
        week_start, week_end = _current_week_range(now)
    else:
        week_start, week_end = _previous_week_range(now)

    try:
        candidates = (
            db.query(Claim)
            .filter(
                Claim.status == ClaimStatusEnum.approved,
                Claim.created_at >= week_start,
                Claim.created_at < week_end,
            )
            .order_by(Claim.worker_id.asc(), Claim.created_at.asc())
            .all()
        )

        grouped: dict[tuple[str, str], list[Claim]] = defaultdict(list)
        for claim in candidates:
            existing_payout = db.query(Payout).filter(Payout.claim_id == claim.id).first()
            if existing_payout is not None:
                continue
            grouped[(str(claim.worker_id), str(claim.policy_id))].append(claim)

        processed_claims = 0
        created_payouts = 0
        total_settled_amount = 0.0

        for (_, policy_id), claims in grouped.items():
            if not claims:
                continue

            policy = db.query(Policy).filter(Policy.id == claims[0].policy_id).first()
            if policy is None:
                continue

            requested_total = sum(float(c.payout_amount or 0.0) for c in claims)
            payable_total = min(float(policy.max_weekly_coverage), requested_total)
            if requested_total <= 0 or payable_total <= 0:
                continue

            ratio = min(1.0, payable_total / requested_total)
            distributed = 0.0

            for idx, claim in enumerate(claims):
                raw_amount = float(claim.payout_amount or 0.0)
                if idx == len(claims) - 1:
                    amount = round(max(payable_total - distributed, 0.0), 2)
                else:
                    amount = round(raw_amount * ratio, 2)
                    distributed += amount

                if amount <= 0:
                    continue

                payout = Payout(
                    claim_id=claim.id,
                    worker_id=claim.worker_id,
                    amount=amount,
                    payment_method=PaymentMethodEnum.upi,
                    payment_status=PaymentStatusEnum.completed,
                    razorpay_order_id=(
                        f"AUTO-WEEKLY-{week_start.strftime('%Y%m%d')}-{str(claim.id).replace('-', '')[:10]}"
                    ),
                    completed_at=now,
                )
                db.add(payout)
                claim.status = ClaimStatusEnum.paid
                claim.payout_amount = amount
                db.add(claim)

                processed_claims += 1
                created_payouts += 1
                total_settled_amount += amount

        db.commit()
        return {
            "mode": mode,
            "week_start": week_start.isoformat(),
            "week_end": week_end.isoformat(),
            "processed_claims": processed_claims,
            "created_payouts": created_payouts,
            "total_settled_amount": round(total_settled_amount, 2),
        }
    except Exception:
        logger.exception("Scheduler weekly settlement failed")
        db.rollback()
        raise
    finally:
        db.close()


async def settle_weekly_payouts() -> None:
    """Scheduled wrapper for weekly settlement."""
    try:
        run_weekly_settlement_now()
    except Exception:
        logger.exception("Scheduled settle_weekly_payouts failed")


def start_scheduler() -> None:
    """Register and start scheduler jobs if not already running."""
    if scheduler.running:
        return

    scheduler.add_job(poll_all_zones, "interval", minutes=10, id="poll_all_zones", replace_existing=True)
    scheduler.add_job(
        recalculate_weekly_premiums,
        "cron",
        day_of_week="mon",
        hour=0,
        minute=30,
        id="recalculate_weekly_premiums",
        replace_existing=True,
    )
    scheduler.add_job(
        settle_weekly_payouts,
        "cron",
        day_of_week="mon",
        hour=0,
        minute=35,
        id="settle_weekly_payouts",
        replace_existing=True,
    )
    scheduler.start()


def stop_scheduler() -> None:
    """Gracefully stop scheduler if active."""
    if scheduler.running:
        scheduler.shutdown(wait=False)
