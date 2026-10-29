"""
Booking service — state machine transitions for bookings.

Every transition:
1. Validates the current state allows the requested transition.
2. Applies credit changes via credit_service.
3. Writes to the audit log via audit_service.
4. Sends an in-app notification via notification_service.
"""
from __future__ import annotations

from math import ceil
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.clock import app_now
from app.models import ActionProposal, Booking, Equipment, User
from app.services import audit_service, credit_service, notification_service

CHECKIN_WINDOW_MINUTES = 15


def _get_booking_or_404(db: Session, booking_id: int) -> Booking:
    b = db.query(Booking).filter(Booking.id == booking_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found.")
    return b


def _assert_status(booking: Booking, *allowed: str) -> None:
    if booking.status not in allowed:
        raise HTTPException(
            status_code=409,
            detail=f"Booking is in status '{booking.status}'; expected one of {list(allowed)}.",
        )


def _calc_cost(equipment: Equipment, slot_start, slot_end) -> int:
    hours = ceil((slot_end - slot_start).total_seconds() / 3600)
    return hours * equipment.credit_per_hour


def create_booking(
    db: Session,
    user: User,
    equipment_id: int,
    slot_start,
    slot_end,
    purpose: Optional[str],
) -> Booking:
    equip = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found.")
    if equip.status != "available":
        raise HTTPException(status_code=409, detail=f"Equipment is '{equip.status}', not bookable.")

    duration_hours = (slot_end - slot_start).total_seconds() / 3600
    if duration_hours <= 0:
        raise HTTPException(status_code=422, detail="slot_end must be after slot_start.")
    if duration_hours > equip.max_booking_hours:
        raise HTTPException(
            status_code=422,
            detail=f"Duration {duration_hours:.1f}h exceeds max {equip.max_booking_hours}h.",
        )

    # Conflict check: overlapping PENDING/APPROVED/IN_PROGRESS bookings
    conflict = (
        db.query(Booking)
        .filter(
            Booking.equipment_id == equipment_id,
            Booking.status.in_(["PENDING", "APPROVED", "IN_PROGRESS"]),
            Booking.slot_start < slot_end,
            Booking.slot_end > slot_start,
        )
        .first()
    )
    if conflict:
        raise HTTPException(status_code=409, detail="Slot conflicts with an existing booking.")

    cost = _calc_cost(equip, slot_start, slot_end)

    booking = Booking(
        user_id=user.id,
        equipment_id=equipment_id,
        status="PENDING",
        slot_start=slot_start,
        slot_end=slot_end,
        purpose=purpose,
        credits_held=cost,
    )
    db.add(booking)
    db.flush()

    credit_service.hold_credits(db, user, cost, booking.id)

    audit_service.write_audit(
        db,
        entity_type="booking",
        entity_id=booking.id,
        action="BOOKING_CREATED",
        payload={
            "user_id": user.id,
            "equipment_id": equipment_id,
            "slot_start": str(slot_start),
            "slot_end": str(slot_end),
            "credits_held": cost,
        },
        actor_id=user.id,
        actor_role=user.role,
    )

    notification_service.notify(
        db, user.id,
        title="Booking Submitted",
        message=f"Your booking for '{equip.name}' on {slot_start.strftime('%d %b %Y %H:%M')} is pending manager approval.",
        notif_type="BOOKING_UPDATE",
        entity_type="booking",
        entity_id=booking.id,
    )
    return booking


def approve_booking(
    db: Session, booking_id: int, manager: User, note: Optional[str], decision_reason: Optional[dict]
) -> Booking:
    booking = _get_booking_or_404(db, booking_id)
    _assert_status(booking, "PENDING")

    booking.status = "APPROVED"
    booking.manager_note = note
    booking.decision_reason = decision_reason or {"criterion": "Manager review", "automated": False}

    audit_service.write_audit(
        db,
        entity_type="booking",
        entity_id=booking.id,
        action="BOOKING_APPROVED",
        payload={"manager_id": manager.id, "note": note, "decision_reason": booking.decision_reason},
        actor_id=manager.id,
        actor_role=manager.role,
    )
    notification_service.notify(
        db, booking.user_id,
        title="Booking Approved ✓",
        message=f"Your booking #{booking.id} has been approved. {note or ''}",
        notif_type="BOOKING_UPDATE",
        entity_type="booking",
        entity_id=booking.id,
    )
    return booking


def reject_booking(
    db: Session, booking_id: int, manager: User, note: Optional[str], decision_reason: Optional[dict]
) -> Booking:
    booking = _get_booking_or_404(db, booking_id)
    _assert_status(booking, "PENDING")

    booking.status = "REJECTED"
    booking.manager_note = note
    booking.decision_reason = decision_reason or {"criterion": "Manager review", "automated": False}

    user = db.query(User).filter(User.id == booking.user_id).first()
    credit_service.release_hold(db, user, booking.credits_held, booking.id)

    audit_service.write_audit(
        db,
        entity_type="booking",
        entity_id=booking.id,
        action="BOOKING_REJECTED",
        payload={"manager_id": manager.id, "note": note, "credits_released": booking.credits_held},
        actor_id=manager.id,
        actor_role=manager.role,
    )
    notification_service.notify(
        db, booking.user_id,
        title="Booking Rejected",
        message=f"Your booking #{booking.id} was rejected. {note or ''}",
        notif_type="BOOKING_UPDATE",
        entity_type="booking",
        entity_id=booking.id,
    )
    return booking


def cancel_booking(db: Session, booking_id: int, actor: User) -> Booking:
    booking = _get_booking_or_404(db, booking_id)
    _assert_status(booking, "PENDING", "APPROVED", "IN_PROGRESS", "NO_SHOW_PROPOSED")

    # Regular user can only cancel their own booking
    if actor.role == "user" and booking.user_id != actor.id:
        raise HTTPException(status_code=403, detail="Cannot cancel another user's booking.")

    booking.status = "CANCELLED"

    if booking.credits_held > 0:
        user = db.query(User).filter(User.id == booking.user_id).first()
        credit_service.release_hold(db, user, booking.credits_held, booking.id)

    audit_service.write_audit(
        db,
        entity_type="booking",
        entity_id=booking.id,
        action="BOOKING_CANCELLED",
        payload={"cancelled_by": actor.id, "credits_released": booking.credits_held},
        actor_id=actor.id,
        actor_role=actor.role,
    )
    notification_service.notify(
        db, booking.user_id,
        title="Booking Cancelled",
        message=f"Booking #{booking.id} has been cancelled.",
        notif_type="BOOKING_UPDATE",
        entity_type="booking",
        entity_id=booking.id,
    )
    return booking


def checkin_booking(db: Session, booking_id: int, actor: User) -> Booking:
    booking = _get_booking_or_404(db, booking_id)
    _assert_status(booking, "APPROVED")

    if actor.role == "user" and booking.user_id != actor.id:
        raise HTTPException(status_code=403, detail="Cannot check in for another user.")

    now = app_now()
    delta_minutes = abs((now - booking.slot_start).total_seconds() / 60)
    if delta_minutes > CHECKIN_WINDOW_MINUTES:
        raise HTTPException(
            status_code=409,
            detail=f"Check-in is only allowed within ±{CHECKIN_WINDOW_MINUTES} min of slot start. "
                   f"Current offset: {delta_minutes:.1f} min.",
        )

    booking.status = "IN_PROGRESS"
    booking.checked_in_at = now

    audit_service.write_audit(
        db,
        entity_type="booking",
        entity_id=booking.id,
        action="BOOKING_CHECKIN",
        payload={"checked_in_at": str(now), "actor_id": actor.id},
        actor_id=actor.id,
        actor_role=actor.role,
    )
    return booking


def checkout_booking(db: Session, booking_id: int, actor: User) -> Booking:
    booking = _get_booking_or_404(db, booking_id)
    _assert_status(booking, "IN_PROGRESS")

    if actor.role == "user" and booking.user_id != actor.id:
        raise HTTPException(status_code=403, detail="Cannot check out for another user.")

    now = app_now()
    booking.status = "COMPLETED"
    booking.checked_out_at = now
    booking.credits_charged = booking.credits_held

    user = db.query(User).filter(User.id == booking.user_id).first()
    credit_service.deduct_credits(db, user, booking.credits_charged, booking.id, actor.id)

    audit_service.write_audit(
        db,
        entity_type="booking",
        entity_id=booking.id,
        action="BOOKING_CHECKOUT",
        payload={
            "checked_out_at": str(now),
            "credits_charged": booking.credits_charged,
            "actor_id": actor.id,
        },
        actor_id=actor.id,
        actor_role=actor.role,
    )
    notification_service.notify(
        db, booking.user_id,
        title="Session Complete ✓",
        message=f"Booking #{booking.id} completed. {booking.credits_charged} credits charged.",
        notif_type="BOOKING_UPDATE",
        entity_type="booking",
        entity_id=booking.id,
    )
    return booking


def propose_no_show(db: Session, booking: Booking) -> ActionProposal:
    """
    Called by APScheduler when check-in window has passed without a check-in.
    Creates a PENDING proposal — manager must confirm before credits are forfeited.
    """
    rationale = (
        f"Booking #{booking.id} (equipment_id={booking.equipment_id}) had slot_start "
        f"{booking.slot_start} UTC. No check-in was recorded. "
        f"app_now={app_now()} UTC (>{CHECKIN_WINDOW_MINUTES} min past slot_start). "
        f"Proposing NO_SHOW status and forfeiture of {booking.credits_held} credits."
    )
    proposal = ActionProposal(
        proposal_type="NO_SHOW_PENALTY",
        entity_type="booking",
        entity_id=booking.id,
        triggered_by="scheduler",
        rationale=rationale,
        proposed_payload={
            "new_status": "NO_SHOW",
            "credits_to_forfeit": booking.credits_held,
            "booking_id": booking.id,
            "user_id": booking.user_id,
        },
        status="PENDING",
    )
    db.add(proposal)
    db.flush()

    booking.status = "NO_SHOW_PROPOSED"

    audit_service.write_audit(
        db,
        entity_type="booking",
        entity_id=booking.id,
        action="BOOKING_NO_SHOW_PROPOSED",
        payload={"proposal_id": proposal.id, "credits_at_risk": booking.credits_held},
        actor_id=None,
        actor_role="system",
        rationale=rationale,
    )
    notification_service.notify(
        db, booking.user_id,
        title="No-Show Flagged",
        message=f"Booking #{booking.id} has been flagged as a potential no-show. A manager will review.",
        notif_type="BOOKING_UPDATE",
        entity_type="booking",
        entity_id=booking.id,
    )
    return proposal

