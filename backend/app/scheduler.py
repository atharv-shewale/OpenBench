"""
APScheduler background jobs.

Non-negotiable rules:
- Jobs only PROPOSE actions; they never apply penalties directly.
- Every proposal is stored in action_proposals with a plain-English rationale.
- A manager must CONFIRM before any credit/status change happens.
- All time comparisons use app_now().
"""
from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)
scheduler = BackgroundScheduler()


def _check_no_shows() -> None:
    """
    Scan APPROVED bookings whose slot_start has passed by >15 minutes
    without a check-in. Propose NO_SHOW for each.
    """
    from app.clock import app_now
    from app.database import SessionLocal
    from app.models import Booking
    from app.services.booking_service import CHECKIN_WINDOW_MINUTES, propose_no_show

    db = SessionLocal()
    try:
        now = app_now()
        overdue = (
            db.query(Booking)
            .filter(
                Booking.status == "APPROVED",
                Booking.checked_in_at.is_(None),
                # slot_start + window has elapsed
            )
            .all()
        )
        for booking in overdue:
            minutes_past = (now - booking.slot_start).total_seconds() / 60
            if minutes_past > CHECKIN_WINDOW_MINUTES:
                logger.info(
                    "Proposing NO_SHOW for booking #%s (%.0f min overdue)",
                    booking.id, minutes_past,
                )
                propose_no_show(db, booking)
        db.commit()
    except Exception:
        logger.exception("Error in _check_no_shows job")
        db.rollback()
    finally:
        db.close()


def _notify_waitlist_on_cancellations() -> None:
    """
    Find WAITING waitlist entries whose blocking booking is now
    CANCELLED/REJECTED, and move them to NOTIFIED.
    """
    from app.clock import app_now
    from app.database import SessionLocal
    from app.models import Booking, WaitlistEntry
    from app.services.notification_service import notify

    db = SessionLocal()
    try:
        now = app_now()
        entries = (
            db.query(WaitlistEntry)
            .filter(WaitlistEntry.status == "WAITING")
            .all()
        )
        for entry in entries:
            if entry.original_booking_id:
                blocking = db.query(Booking).filter(
                    Booking.id == entry.original_booking_id
                ).first()
                if blocking and blocking.status in ("CANCELLED", "REJECTED"):
                    entry.status = "NOTIFIED"
                    entry.notified_at = now
                    notify(
                        db,
                        user_id=entry.user_id,
                        title="Slot Available!",
                        message=(
                            f"A slot opened up for equipment #{entry.equipment_id} "
                            f"on {entry.desired_start.strftime('%d %b %Y %H:%M')}. Book now!"
                        ),
                        notif_type="WAITLIST",
                        entity_type="equipment",
                        entity_id=entry.equipment_id,
                    )
        db.commit()
    except Exception:
        logger.exception("Error in _notify_waitlist_on_cancellations job")
        db.rollback()
    finally:
        db.close()


def start_scheduler() -> None:
    scheduler.add_job(
        _check_no_shows,
        trigger=IntervalTrigger(minutes=2),
        id="check_no_shows",
        replace_existing=True,
        name="No-show detector (proposes, does not apply)",
    )
    scheduler.add_job(
        _notify_waitlist_on_cancellations,
        trigger=IntervalTrigger(minutes=5),
        id="notify_waitlist",
        replace_existing=True,
        name="Waitlist notifier",
    )
    scheduler.start()
    logger.info("APScheduler started with %d jobs.", len(scheduler.get_jobs()))


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")

