"""
Waitlist service — deterministic ranking and automatic promotion on cancellation.

Features:
1. Join waitlist with ranking score computed via allocation_engine.compute_waitlist_score().
2. Saves complete score breakdown for "Why this outcome?".
3. Auto-promotes top-ranked waitlisted user when a booking is cancelled or rejected.
4. Holds credits, converts into PENDING booking, and notifies the promoted user.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException

from app.clock import app_now
from app.models import Booking, Equipment, User, WaitlistEntry
from app.services import audit_service, credit_service, notification_service
from app.services.allocation_engine import compute_waitlist_score


def _calc_recent_hours(db: Session, user_id: int, current_time: datetime) -> float:
    """Calculates hours completed in the last 7 rolling days."""
    seven_days_ago = current_time - timedelta(days=7)
    recent_bookings = (
        db.query(Booking)
        .filter(
            Booking.user_id == user_id,
            Booking.status.in_(["COMPLETED", "IN_PROGRESS", "APPROVED"]),
            Booking.slot_start >= seven_days_ago,
        )
        .all()
    )
    total_seconds = sum((b.slot_end - b.slot_start).total_seconds() for b in recent_bookings)
    return total_seconds / 3600.0


def join_waitlist(
    db: Session,
    user: User,
    equipment_id: int,
    desired_start: datetime,
    desired_end: datetime,
    purpose: Optional[str] = None,
    priority_tier: str = "STANDARD",
    group_name: Optional[str] = None,
) -> WaitlistEntry:
    equip = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found.")

    now = app_now()

    # User usage stats
    past_completed = db.query(Booking).filter(
        Booking.user_id == user.id, Booking.status == "COMPLETED"
    ).count()
    recent_hours = _calc_recent_hours(db, user.id, now)

    # Compute waitlist score
    score_breakdown = compute_waitlist_score(
        priority_tier=priority_tier,
        total_past_completed_bookings=past_completed,
        recent_weekly_hours_used=recent_hours,
        waitlist_created_at=now,
        evaluation_time=now,
        strike_count=user.strike_count,
    )

    entry = WaitlistEntry(
        user_id=user.id,
        equipment_id=equipment_id,
        desired_start=desired_start,
        desired_end=desired_end,
        purpose=purpose,
        priority_tier=priority_tier,
        group_name=group_name,
        ranking_score=score_breakdown.total_score,
        score_breakdown=score_breakdown.__dict__,
        status="WAITING",
    )
    db.add(entry)
    db.flush()

    audit_service.write_audit(
        db,
        entity_type="waitlist",
        entity_id=entry.id,
        action="WAITLIST_JOINED",
        payload={
            "equipment_id": equipment_id,
            "desired_start": str(desired_start),
            "desired_end": str(desired_end),
            "ranking_score": score_breakdown.total_score,
            "score_breakdown": score_breakdown.__dict__,
        },
        actor_id=user.id,
        actor_role=user.role,
        rationale=score_breakdown.explanation_summary,
    )
    return entry


def auto_promote_waitlist_on_cancellation(
    db: Session,
    cancelled_booking: Booking,
) -> Optional[Booking]:
    """
    Called whenever an existing booking is CANCELLED or REJECTED.
    Finds waitlist entries overlapping the freed slot, re-ranks them dynamically
    based on waiting time, auto-promotes the #1 candidate, and creates a PENDING booking.
    """
    now = app_now()

    # Find candidate waitlist entries overlapping the freed slot window
    candidates = (
        db.query(WaitlistEntry)
        .filter(
            WaitlistEntry.equipment_id == cancelled_booking.equipment_id,
            WaitlistEntry.status == "WAITING",
            WaitlistEntry.desired_start < cancelled_booking.slot_end,
            WaitlistEntry.desired_end > cancelled_booking.slot_start,
        )
        .all()
    )

    if not candidates:
        return None

    # Re-evaluate ranking score for all candidates up to current moment (includes elapsed waiting-time bonus)
    scored_candidates = []
    for entry in candidates:
        user = db.query(User).filter(User.id == entry.user_id).first()
        if not user or not user.is_active or user.strike_count >= 3:
            continue

        past_completed = db.query(Booking).filter(
            Booking.user_id == user.id, Booking.status == "COMPLETED"
        ).count()
        recent_hours = _calc_recent_hours(db, user.id, now)

        breakdown = compute_waitlist_score(
            priority_tier=entry.priority_tier,
            total_past_completed_bookings=past_completed,
            recent_weekly_hours_used=recent_hours,
            waitlist_created_at=entry.created_at,
            evaluation_time=now,
            strike_count=user.strike_count,
        )

        entry.ranking_score = breakdown.total_score
        entry.score_breakdown = breakdown.__dict__
        scored_candidates.append((entry, user, breakdown))

    if not scored_candidates:
        return None

    # Sort descending by total score
    scored_candidates.sort(key=lambda x: x[2].total_score, reverse=True)
    winner_entry, winner_user, winner_breakdown = scored_candidates[0]

    equip = db.query(Equipment).filter(Equipment.id == cancelled_booking.equipment_id).first()
    # Check spendable credits for winner
    cost = int(max(1, (winner_entry.desired_end - winner_entry.desired_start).total_seconds() / 3600.0) * equip.credit_per_hour) + equip.deposit_credits
    spendable = winner_user.credit_balance - winner_user.credit_held

    if spendable < cost:
        # User cannot afford it; mark entry NOTIFIED so they can top up manually
        winner_entry.status = "NOTIFIED"
        winner_entry.notified_at = now
        notification_service.notify(
            db,
            user_id=winner_user.id,
            title="Slot Available — Insufficient Credits",
            message=f"You topped the waitlist for '{equip.name}', but lack sufficient spendable credits ({spendable}/{cost} cr). Please top up.",
            notif_type="WAITLIST",
            entity_type="equipment",
            entity_id=equip.id,
        )
        return None

    # Auto-promote: create PENDING reservation and hold credits
    promoted_booking = Booking(
        user_id=winner_user.id,
        equipment_id=equip.id,
        status="PENDING",
        slot_start=winner_entry.desired_start,
        slot_end=winner_entry.desired_end,
        purpose=winner_entry.purpose,
        priority_tier=winner_entry.priority_tier,
        group_name=winner_entry.group_name,
        credits_held=cost,
    )
    db.add(promoted_booking)
    db.flush()

    credit_service.hold_credits(db, winner_user, cost, promoted_booking.id)

    winner_entry.status = "PROMOTED"
    winner_entry.notified_at = now

    audit_service.write_audit(
        db,
        entity_type="waitlist",
        entity_id=winner_entry.id,
        action="WAITLIST_AUTO_PROMOTED",
        payload={
            "waitlist_id": winner_entry.id,
            "promoted_booking_id": promoted_booking.id,
            "user_id": winner_user.id,
            "final_score": winner_breakdown.total_score,
            "score_breakdown": winner_breakdown.__dict__,
        },
        actor_id=None,
        actor_role="system",
        rationale=f"Auto-promoted top-ranked waitlisted user: {winner_breakdown.explanation_summary}",
    )

    notification_service.notify(
        db,
        user_id=winner_user.id,
        title="Waitlist Slot Promoted! 🎉",
        message=(
            f"You were auto-promoted for '{equip.name}' on "
            f"{winner_entry.desired_start.strftime('%d %b %Y %H:%M')}. "
            f"Why this outcome? {winner_breakdown.explanation_summary}"
        ),
        notif_type="BOOKING_UPDATE",
        entity_type="booking",
        entity_id=promoted_booking.id,
    )
    return promoted_booking

