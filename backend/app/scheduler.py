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


def _dispatch_reminders_and_overdue_alerts() -> None:
    """
    Checks:
    1. Upcoming APPROVED sessions starting in ~30 minutes -> sends REMINDER notification.
    2. IN_PROGRESS sessions past slot_end -> sends OVERDUE_RETURN notification and alert.
    """
    from datetime import timedelta
    from app.clock import app_now
    from app.database import SessionLocal
    from app.models import Booking
    from app.services.notification_service import notify

    db = SessionLocal()
    try:
        now = app_now()

        # 1. 30-Minute Reminders
        upcoming_window_start = now + timedelta(minutes=20)
        upcoming_window_end = now + timedelta(minutes=35)
        remindable = (
            db.query(Booking)
            .filter(
                Booking.status == "APPROVED",
                Booking.slot_start >= upcoming_window_start,
                Booking.slot_start <= upcoming_window_end,
            )
            .all()
        )
        for b in remindable:
            notify(
                db,
                user_id=b.user_id,
                title="Upcoming Session Reminder 🔔",
                message=(
                    f"Reminder: Your booking #{b.id} begins at "
                    f"{b.slot_start.strftime('%H:%M')} UTC. "
                    f"Please remember to bring your student/MSME identification and scan the bench QR code to check in."
                ),
                notif_type="REMINDER",
                entity_type="booking",
                entity_id=b.id,
            )

        # 2. Overdue Return Alerts
        overdue_active = (
            db.query(Booking)
            .filter(
                Booking.status == "IN_PROGRESS",
                Booking.slot_end < now,
            )
            .all()
        )
        for b in overdue_active:
            mins_overdue = int((now - b.slot_end).total_seconds() / 60)
            notify(
                db,
                user_id=b.user_id,
                title="Session Overdue — Return Bench ⚠️",
                message=(
                    f"Your active session for booking #{b.id} ended {mins_overdue} minute(s) ago at "
                    f"{b.slot_end.strftime('%H:%M')} UTC. "
                    f"Please complete checkout immediately to avoid penalty points or request an extension."
                ),
                notif_type="OVERDUE_RETURN",
                entity_type="booking",
                entity_id=b.id,
            )

        db.commit()
    except Exception:
        logger.exception("Error in _dispatch_reminders_and_overdue_alerts job")
        db.rollback()
    finally:
        db.close()


def _check_auto_release_unclaimed() -> None:
    """
    Scans for APPROVED bookings without check-in or usage signal
    past the grace period, auto-releases the slot, promotes the waitlist,
    and stages a PROPOSED strike for manager review.
    """
    from app.database import SessionLocal
    from app.services.auto_release_service import scan_and_auto_release_unclaimed_bookings

    db = SessionLocal()
    try:
        scan_and_auto_release_unclaimed_bookings(db, grace_minutes=20)
    except Exception:
        logger.exception("Error in _check_auto_release_unclaimed job")
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
    scheduler.add_job(
        _dispatch_reminders_and_overdue_alerts,
        trigger=IntervalTrigger(minutes=5),
        id="reminders_and_overdue",
        replace_existing=True,
        name="Session reminders and overdue returns notifier",
    )
    scheduler.add_job(
        _check_auto_release_unclaimed,
        trigger=IntervalTrigger(minutes=2),
        id="auto_release_unclaimed",
        replace_existing=True,
        name="Auto-release unclaimed bookings after grace period",
    )
    scheduler.start()
    logger.info("APScheduler started with %d jobs.", len(scheduler.get_jobs()))


def stop_scheduler() -> None:
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler stopped.")

