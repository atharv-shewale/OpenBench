"""
Auto-Release & Strike Proposal Service.
Scans for approved bookings that received neither check-in nor usage telemetry signals
within the configurable grace period (using app_now()).

Non-Negotiable Rules Enforced:
1. Slot is auto-released and waitlist is promoted.
2. User is notified with a plain-language reason.
3. Action is explicitly reversible by a lab manager.
4. Strikes are ONLY PROPOSED — a human manager confirms or dismisses, and the user can contest.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any, Dict, List, Optional

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.clock import app_now
from app.models import ActionProposal, Booking, Equipment, Strike, User
from app.services import audit_service, credit_service, notification_service

logger = logging.getLogger(__name__)

DEFAULT_GRACE_PERIOD_MINUTES = 20


def scan_and_auto_release_unclaimed_bookings(
    db: Session, grace_minutes: int = DEFAULT_GRACE_PERIOD_MINUTES
) -> List[Booking]:
    """
    Finds APPROVED bookings whose slot_start + grace_minutes has passed without
    either an explicit check-in or a simulated/IoT usage signal.
    Auto-releases the slot, releases held credits, promotes waitlist,
    notifies the user, and stages a PROPOSED strike for human review.
    """
    now = app_now()
    released_bookings: List[Booking] = []

    approved_bookings = db.query(Booking).filter(Booking.status == "APPROVED").all()

    for booking in approved_bookings:
        cutoff = booking.slot_start + timedelta(minutes=grace_minutes)
        if now <= cutoff:
            continue

        # Check for check-in or recent usage signal
        has_checked_in = booking.checked_in_at is not None
        has_usage_signal = (
            booking.last_usage_signal_at is not None
            and booking.last_usage_signal_at >= booking.slot_start
        )

        if has_checked_in or has_usage_signal:
            continue

        # Auto-Release conditions met!
        equip = db.query(Equipment).filter(Equipment.id == booking.equipment_id).first()
        user = db.query(User).filter(User.id == booking.user_id).first()

        prev_held = booking.credits_held
        booking.status = "AUTO_RELEASED"
        booking.decision_reason = {
            "reason": (
                f"No check-in or machine usage signal received within {grace_minutes} minutes "
                f"of scheduled start ({booking.slot_start} UTC)."
            ),
            "grace_period_minutes": grace_minutes,
            "automated": True,
            "reversible": True,
            "evaluated_at": now.isoformat(),
        }

        # Release held credits back to user
        if booking.credits_held > 0 and user:
            credit_service.release_hold(db, user, booking.credits_held, booking.id)
            booking.credits_held = 0

        # Auto-promote waitlist candidate for the freed slot
        from app.services.waitlist_service import auto_promote_waitlist_on_cancellation
        auto_promote_waitlist_on_cancellation(db, booking)

        # Notify user with full transparency and reversibility note
        notification_service.notify(
            db,
            user_id=booking.user_id,
            title="Booking Auto-Released (No Activity Detected) ℹ️",
            message=(
                f"Your booking #{booking.id} for {equip.name if equip else 'Equipment'} was auto-released "
                f"because neither check-in nor machine usage signal was detected within {grace_minutes} minutes of start. "
                f"Held credits have been unlocked. This decision is reversible by a lab manager if you were delayed."
            ),
            notif_type="CANCELLATION",
            entity_type="booking",
            entity_id=booking.id,
        )

        # Non-negotiable: Strike is ONLY PROPOSED, never applied automatically
        strike_rationale = (
            f"Automated no-show/no-signal detection: Booking #{booking.id} ({equip.name if equip else 'equipment'}) "
            f"started at {booking.slot_start} UTC with no check-in or usage signal after {grace_minutes}m grace period. "
            f"Proposing 1 strike. Manager confirms or dismisses; user may contest with reason."
        )
        strike_proposal = ActionProposal(
            proposal_type="STRIKE_PROPOSAL",
            entity_type="user",
            entity_id=booking.user_id,
            triggered_by="scheduler",
            rationale=strike_rationale,
            proposed_payload={
                "user_id": booking.user_id,
                "booking_id": booking.id,
                "equipment_id": booking.equipment_id,
                "strike_type": "MISSED_SESSION_NO_SIGNAL",
                "reason": f"No check-in or usage signal within {grace_minutes}m grace window.",
                "explanation": "Human manager review required before strike is confirmed.",
            },
            status="PENDING",
        )
        db.add(strike_proposal)
        db.flush()

        audit_service.write_audit(
            db,
            entity_type="booking",
            entity_id=booking.id,
            action="BOOKING_AUTO_RELEASED",
            payload={
                "booking_id": booking.id,
                "grace_minutes": grace_minutes,
                "credits_released": prev_held,
                "proposed_strike_id": strike_proposal.id,
                "reversible": True,
            },
            actor_id=None,
            actor_role="scheduler",
            rationale=f"Auto-released after {grace_minutes}m without check-in or signal. Strike proposal #{strike_proposal.id} staged.",
        )

        # Notify user about proposed strike with contestation instructions
        notification_service.notify(
            db,
            user_id=booking.user_id,
            title="Notice: Strike Proposed ⚠️",
            message=(
                f"A strike has been proposed for missed session #{booking.id}. "
                f"You may submit a contestation explanation in your dashboard before a lab manager reviews it."
            ),
            notif_type="STRIKE",
            entity_type="action_proposal",
            entity_id=strike_proposal.id,
        )

        released_bookings.append(booking)

    db.commit()
    return released_bookings


def reverse_auto_release(
    db: Session, booking_id: int, manager: User, explanation: str
) -> Booking:
    """
    Allows a manager, owner, or admin to reverse an auto-release decision
    if the student/user had a valid delay or excuse.
    Reinstates booking, re-holds credits if applicable, and dismisses any pending strike proposal.
    """
    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if booking.status != "AUTO_RELEASED":
        raise HTTPException(status_code=409, detail=f"Cannot reverse booking in status '{booking.status}'.")

    now = app_now()
    equip = db.query(Equipment).filter(Equipment.id == booking.equipment_id).first()
    user = db.query(User).filter(User.id == booking.user_id).first()

    # Determine reinstated status: IN_PROGRESS if currently within slot, else APPROVED
    new_status = "IN_PROGRESS" if booking.slot_start <= now <= booking.slot_end else "APPROVED"
    booking.status = new_status
    booking.manager_note = f"Auto-release reversed by {manager.full_name}: {explanation}"

    # Re-hold credits if user has balance
    cost = equip.credit_per_hour * max(1, int((booking.slot_end - booking.slot_start).total_seconds() / 3600))
    if user.credit_balance - user.credit_held >= cost:
        credit_service.hold_credits(db, user, cost, booking.id)
        booking.credits_held = cost

    # Dismiss any pending strike proposals associated with this booking
    proposals = (
        db.query(ActionProposal)
        .filter(
            ActionProposal.proposal_type == "STRIKE_PROPOSAL",
            ActionProposal.entity_id == booking.user_id,
            ActionProposal.status.in_(["PENDING", "CONTESTED"]),
        )
        .all()
    )
    for p in proposals:
        if p.proposed_payload.get("booking_id") == booking.id:
            p.status = "REJECTED"
            p.reviewed_by = manager.id
            p.reviewed_at = now
            p.review_note = f"Dismissed upon auto-release reversal: {explanation}"

    audit_service.write_audit(
        db,
        entity_type="booking",
        entity_id=booking.id,
        action="BOOKING_AUTO_RELEASE_REVERSED",
        payload={"manager_id": manager.id, "explanation": explanation, "new_status": new_status},
        actor_id=manager.id,
        actor_role=manager.role,
        rationale=f"Auto-release reversed: {explanation}",
    )

    notification_service.notify(
        db,
        user_id=booking.user_id,
        title="Booking Reinstated ✓",
        message=f"Your booking #{booking.id} has been reinstated by lab manager {manager.full_name}. Rationale: {explanation}",
        notif_type="BOOKING_UPDATE",
        entity_type="booking",
        entity_id=booking.id,
    )
    db.commit()
    db.refresh(booking)
    return booking


def contest_proposal(
    db: Session, proposal_id: int, user: User, contestation_note: str
) -> ActionProposal:
    """
    Enables a user to contest a proposed strike or penalty with their defense/explanation
    before human manager confirmation.
    """
    proposal = db.query(ActionProposal).filter(ActionProposal.id == proposal_id).first()
    if not proposal:
        raise HTTPException(status_code=404, detail="Proposal not found.")

    if user.role == "user" and proposal.entity_id != user.id:
        raise HTTPException(status_code=403, detail="Cannot contest a proposal for another user.")

    if proposal.status not in ("PENDING", "CONTESTED"):
        raise HTTPException(status_code=409, detail=f"Cannot contest proposal with status '{proposal.status}'.")

    now = app_now()
    proposal.status = "CONTESTED"
    proposal.contested_at = now
    proposal.contestation_note = contestation_note

    audit_service.write_audit(
        db,
        entity_type="action_proposal",
        entity_id=proposal.id,
        action="PROPOSAL_CONTESTED",
        payload={"user_id": user.id, "contestation_note": contestation_note},
        actor_id=user.id,
        actor_role=user.role,
        rationale=f"User contested proposal: {contestation_note}",
    )
    db.commit()
    db.refresh(proposal)
    return proposal
