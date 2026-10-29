"""
Booking service — state machine transitions for bookings,
integrated with the pure eligibility engine and counterfactual generator.

Non-negotiables enforced:
1. Rejects impossible requests early using evaluate_booking_eligibility().
2. Prevents overlapping approved/active bookings inside an atomic transaction.
3. Holds credits safely and rolls back on failure.
4. Every state transition and rejection is appended to the hash-chained audit log.
5. On conflict or failure, generates actionable counterfactual explanations.
"""
from __future__ import annotations

from datetime import datetime, timedelta
from math import ceil
from typing import Any, Dict, List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.clock import app_now
from app.models import (
    ActionProposal, Booking, ConditionReport, Equipment, EquipmentAvailabilityWindow,
    Lab, User, UserCredential,
)
from app.services import audit_service, credit_service, notification_service
from app.services.eligibility_engine import evaluate_booking_eligibility
from app.services.counterfactual_engine import generate_counterfactual_explanations
from app.services.storage_service import generate_signed_url
from app.services.photo_diff_service import compare_condition_photos

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
    hours = max(1, ceil((slot_end - slot_start).total_seconds() / 3600))
    return (hours * equipment.credit_per_hour) + equipment.deposit_credits


def create_booking(
    db: Session,
    user: User,
    equipment_id: int,
    slot_start,
    slot_end,
    purpose: Optional[str] = None,
    priority_tier: str = "STANDARD",
    group_name: Optional[str] = None,
    has_supervisor_signoff: bool = False,
    supervisor_name: Optional[str] = None,
) -> Booking:
    equip = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found.")
    if equip.status != "available":
        raise HTTPException(status_code=409, detail=f"Equipment is '{equip.status}', not bookable.")

    now = app_now()
    user_creds_db = db.query(UserCredential).filter(UserCredential.user_id == user.id).all()
    user_creds = [
        {
            "credential_type": c.credential_type,
            "is_verified": c.is_verified,
            "expires_at": c.expires_at,
        }
        for c in user_creds_db
    ]

    windows_db = db.query(EquipmentAvailabilityWindow).filter(
        EquipmentAvailabilityWindow.equipment_id == equipment_id
    ).all()
    avail_windows = [
        {"day_of_week": w.day_of_week, "start_time": w.start_time, "end_time": w.end_time}
        for w in windows_db
    ]

    user_data = {
        "is_active": user.is_active,
        "strike_count": user.strike_count,
        "role": user.role,
        "spendable_credits": user.credit_balance - user.credit_held,
        "credentials": user_creds,
    }

    equipment_data = {
        "credit_per_hour": equip.credit_per_hour,
        "deposit_credits": equip.deposit_credits,
        "max_booking_hours": equip.max_booking_hours,
        "required_credentials": equip.required_credentials or [],
        "rules": equip.rules or {},
        "availability_windows": avail_windows,
    }

    booking_req = {
        "slot_start": slot_start,
        "slot_end": slot_end,
        "has_supervisor_signoff": has_supervisor_signoff,
        "supervisor_name": supervisor_name,
    }

    # Fetch existing active bookings for slot overlap check & counterfactual search
    existing_bookings_db = (
        db.query(Booking)
        .filter(
            Booking.equipment_id == equipment_id,
            Booking.status.in_(["APPROVED", "IN_PROGRESS", "PENDING"]),
        )
        .all()
    )
    existing_bookings = [
        {"slot_start": b.slot_start, "slot_end": b.slot_end, "id": b.id, "status": b.status}
        for b in existing_bookings_db
    ]

    # 1. Pure Eligibility Engine Check
    eval_result = evaluate_booking_eligibility(user_data, equipment_data, booking_req, now)

    # 1b. Allocation Engine Constraints (Weekly caps, Active bookings limit, Advance window, Prime cooldown)
    from app.services.allocation_engine import evaluate_allocation_constraints, is_prime_slot

    # Count user's current active reservations
    active_count = db.query(Booking).filter(
        Booking.user_id == user.id,
        Booking.status.in_(["PENDING", "APPROVED", "IN_PROGRESS"]),
    ).count()

    # User's recent completed/approved hours in last 7 days
    seven_days_ago = now - timedelta(days=7)
    recent_user_bookings = db.query(Booking).filter(
        Booking.user_id == user.id,
        Booking.status.in_(["COMPLETED", "IN_PROGRESS", "APPROVED"]),
        Booking.slot_start >= seven_days_ago,
    ).all()
    recent_user_hours = sum((b.slot_end - b.slot_start).total_seconds() for b in recent_user_bookings) / 3600.0

    recent_group_hours = 0.0
    if group_name:
        recent_group_bookings = db.query(Booking).filter(
            Booking.group_name == group_name,
            Booking.status.in_(["COMPLETED", "IN_PROGRESS", "APPROVED"]),
            Booking.slot_start >= seven_days_ago,
        ).all()
        recent_group_hours = sum((b.slot_end - b.slot_start).total_seconds() for b in recent_group_bookings) / 3600.0

    # Last prime slot on this equipment for this user
    last_prime_booking = (
        db.query(Booking)
        .filter(
            Booking.user_id == user.id,
            Booking.equipment_id == equipment_id,
            Booking.status.in_(["COMPLETED", "APPROVED", "IN_PROGRESS"]),
        )
        .order_by(Booking.slot_end.desc())
        .first()
    )
    last_prime_slot_end = last_prime_booking.slot_end if last_prime_booking and is_prime_slot(last_prime_booking.slot_start, last_prime_booking.slot_end) else None

    alloc_eval = evaluate_allocation_constraints(
        current_time=now,
        slot_start=slot_start,
        slot_end=slot_end,
        active_booking_count=active_count,
        recent_user_hours=recent_user_hours,
        recent_group_hours=recent_group_hours,
        has_group=bool(group_name),
        last_prime_slot_end=last_prime_slot_end,
    )

    if not alloc_eval["allowed"]:
        eval_result.is_eligible = False
        eval_result.reasons_failed.append(alloc_eval["first_rejection_reason"])

    # 2. Overlap Conflict Check
    conflict = next(
        (b for b in existing_bookings if b["slot_start"] < slot_end and b["slot_end"] > slot_start),
        None,
    )

    if not eval_result.is_eligible or conflict is not None:
        # Generate counterfactual actionable recommendations
        counterfactuals = generate_counterfactual_explanations(
            user_data=user_data,
            equipment_data=equipment_data,
            booking_request=booking_req,
            current_time=now,
            existing_bookings=existing_bookings,
        )

        rejection_reason = (
            "Slot conflicts with an existing reservation."
            if conflict else "; ".join(eval_result.reasons_failed)
        )

        # Audit log the failed request attempt for security and fairness review
        audit_service.write_audit(
            db,
            entity_type="booking",
            entity_id=0,
            action="BOOKING_REQUEST_REJECTED_EARLY",
            payload={
                "user_id": user.id,
                "equipment_id": equipment_id,
                "slot_start": str(slot_start),
                "slot_end": str(slot_end),
                "rejection_reasons": eval_result.reasons_failed if not conflict else ["Slot conflict"],
                "counterfactuals": counterfactuals,
            },
            actor_id=user.id,
            actor_role=user.role,
            rationale=rejection_reason,
        )
        db.commit()

        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT if conflict else status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "message": rejection_reason,
                "reasons": eval_result.reasons_failed if not conflict else ["Slot is already reserved by another user."],
                "counterfactuals": counterfactuals,
            },
        )

    # 3. Request is fully eligible and conflict-free -> Proceed atomically
    cost = _calc_cost(equip, slot_start, slot_end)

    booking = Booking(
        user_id=user.id,
        equipment_id=equipment_id,
        status="PENDING",
        slot_start=slot_start,
        slot_end=slot_end,
        purpose=purpose,
        priority_tier=priority_tier,
        group_name=group_name,
        has_supervisor_signoff=has_supervisor_signoff,
        supervisor_name=supervisor_name,
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
            "priority_tier": priority_tier,
            "credits_held": cost,
        },
        actor_id=user.id,
        actor_role=user.role,
    )

    notification_service.notify(
        db, user.id,
        title="Booking Submitted",
        message=f"Your booking for '{equip.name}' on {slot_start.strftime('%d %b %Y %H:%M')} is submitted.",
        notif_type="BOOKING_UPDATE",
        entity_type="booking",
        entity_id=booking.id,
    )
    return booking


def approve_booking(
    db: Session,
    booking_id: int,
    manager: User,
    note: Optional[str],
    decision_reason: Optional[dict],
    override: bool = False,
) -> Booking:
    booking = _get_booking_or_404(db, booking_id)
    _assert_status(booking, "PENDING")

    # If owner override is active, check permission
    if override:
        if manager.role not in ("owner", "admin"):
            raise HTTPException(status_code=403, detail="Only owners or admins can execute an override approval.")

    # Atomic transactional check for conflicts before final approval (unless owner override)
    if not override:
        overlap = (
            db.query(Booking)
            .filter(
                Booking.equipment_id == booking.equipment_id,
                Booking.id != booking.id,
                Booking.status.in_(["APPROVED", "IN_PROGRESS"]),
                Booking.slot_start < booking.slot_end,
                Booking.slot_end > booking.slot_start,
            )
            .first()
        )
        if overlap:
            raise HTTPException(
                status_code=409,
                detail=f"Cannot approve: slot overlaps with confirmed Booking #{overlap.id}. Owner override required.",
            )

    booking.status = "APPROVED"
    booking.manager_note = note
    booking.decision_reason = decision_reason or {
        "criterion": "Owner Override" if override else "Manager review",
        "automated": False,
        "override": override,
    }

    action_name = "BOOKING_APPROVED_OVERRIDE" if override else "BOOKING_APPROVED"

    audit_service.write_audit(
        db,
        entity_type="booking",
        entity_id=booking.id,
        action=action_name,
        payload={"manager_id": manager.id, "note": note, "decision_reason": booking.decision_reason, "override": override},
        actor_id=manager.id,
        actor_role=manager.role,
        rationale=note or ("Owner administrative override approved." if override else "Manager approval"),
    )
    notification_service.notify(
        db, booking.user_id,
        title="Booking Approved ✓" if not override else "Booking Approved by Owner Override ★",
        message=f"Your booking #{booking.id} has been approved. {note or ''}",
        notif_type="APPROVAL",
        entity_type="booking",
        entity_id=booking.id,
    )
    return booking


def reject_booking(
    db: Session, booking_id: int, manager: User, note: str, decision_reason: Optional[dict]
) -> Booking:
    booking = _get_booking_or_404(db, booking_id)
    _assert_status(booking, "PENDING")

    if not note or not note.strip():
        raise HTTPException(status_code=422, detail="A clear rejection reason is mandatory.")

    booking.status = "REJECTED"
    booking.manager_note = note
    booking.decision_reason = decision_reason or {"criterion": "Manager review", "rejection_reason": note, "automated": False}

    user = db.query(User).filter(User.id == booking.user_id).first()
    credit_service.release_hold(db, user, booking.credits_held, booking.id)

    audit_service.write_audit(
        db,
        entity_type="booking",
        entity_id=booking.id,
        action="BOOKING_REJECTED",
        payload={"manager_id": manager.id, "reason": note, "credits_released": booking.credits_held},
        actor_id=manager.id,
        actor_role=manager.role,
        rationale=note,
    )
    notification_service.notify(
        db, booking.user_id,
        title="Booking Rejected",
        message=f"Your booking #{booking.id} was rejected. Reason: {note}",
        notif_type="REJECTION",
        entity_type="booking",
        entity_id=booking.id,
    )

    # Auto-promote waitlist candidate for freed slot
    from app.services.waitlist_service import auto_promote_waitlist_on_cancellation
    auto_promote_waitlist_on_cancellation(db, booking)

    return booking


def extend_booking(
    db: Session, booking_id: int, actor: User, extra_hours: int = 1
) -> Booking:
    """
    Extends an active IN_PROGRESS or APPROVED booking if:
    1. Extra hours <= max_booking_hours
    2. User has enough spendable credits
    3. No overlapping booking exists for the extended slot interval
    """
    booking = _get_booking_or_404(db, booking_id)
    _assert_status(booking, "IN_PROGRESS", "APPROVED")

    if actor.role == "user" and booking.user_id != actor.id:
        raise HTTPException(status_code=403, detail="Cannot extend another user's session.")

    new_end = booking.slot_end + timedelta(hours=extra_hours)
    equip = db.query(Equipment).filter(Equipment.id == booking.equipment_id).first()

    # Check overlap
    overlap = (
        db.query(Booking)
        .filter(
            Booking.equipment_id == booking.equipment_id,
            Booking.id != booking.id,
            Booking.status.in_(["APPROVED", "IN_PROGRESS"]),
            Booking.slot_start < new_end,
            Booking.slot_end > booking.slot_end,
        )
        .first()
    )
    if overlap:
        raise HTTPException(status_code=409, detail="Cannot extend: slot overlaps with an upcoming booking.")

    # Check and hold credits for extension
    cost = extra_hours * equip.credit_per_hour
    user = db.query(User).filter(User.id == booking.user_id).first()
    credit_service.hold_credits(db, user, cost, booking.id)

    booking.slot_end = new_end
    booking.credits_held += cost

    audit_service.write_audit(
        db,
        entity_type="booking",
        entity_id=booking.id,
        action="BOOKING_EXTENDED",
        payload={"extra_hours": extra_hours, "new_end": str(new_end), "extra_cost": cost},
        actor_id=actor.id,
        actor_role=actor.role,
        rationale=f"Session extended by {extra_hours} hour(s).",
    )

    notification_service.notify(
        db,
        user_id=booking.user_id,
        title="Session Extended ⏱️",
        message=f"Booking #{booking.id} has been extended by {extra_hours} hour(s) until {new_end.strftime('%H:%M')}.",
        notif_type="EXTENSION",
        entity_type="booking",
        entity_id=booking.id,
    )
    return booking


def cancel_booking(db: Session, booking_id: int, actor: User) -> Booking:
    booking = _get_booking_or_404(db, booking_id)
    _assert_status(booking, "PENDING", "APPROVED", "IN_PROGRESS", "NO_SHOW_PROPOSED")

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

    # Auto-promote waitlist candidate for freed slot
    from app.services.waitlist_service import auto_promote_waitlist_on_cancellation
    auto_promote_waitlist_on_cancellation(db, booking)

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
            detail=f"Check-in is only allowed within ±{CHECKIN_WINDOW_MINUTES} min of slot start. Current offset: {delta_minutes:.1f} min.",
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


def perform_qr_checkin(
    db: Session,
    booking_id: int,
    actor: User,
    condition: str = "GOOD",
    checklist: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None,
    photos: Optional[List[str]] = None,
) -> Tuple[Booking, ConditionReport]:
    """
    QR-based check-in with pre-flight condition checklist, notes, and photos.
    Confirms identity, verifies the check-in window against app_now(),
    transitions booking to IN_PROGRESS, records the pre-condition report,
    and logs to the append-only audit log.
    """
    booking = _get_booking_or_404(db, booking_id)
    _assert_status(booking, "APPROVED")

    if actor.role not in ("owner", "manager", "admin") and booking.user_id != actor.id:
        raise HTTPException(status_code=403, detail="Cannot check in for another user's booking.")

    now = app_now()
    if now < booking.slot_start - timedelta(minutes=CHECKIN_WINDOW_MINUTES):
        delta = (booking.slot_start - now).total_seconds() / 60
        raise HTTPException(
            status_code=409,
            detail=f"Check-in window opens {CHECKIN_WINDOW_MINUTES} min before slot start. Please wait {delta:.0f} more minutes.",
        )
    if now > booking.slot_end:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot check in: scheduled booking window ended at {booking.slot_end.strftime('%Y-%m-%d %H:%M')}.",
        )

    booking.status = "IN_PROGRESS"
    booking.checked_in_at = now

    flagged = condition in ("DAMAGED", "BROKEN")
    pre_report = ConditionReport(
        booking_id=booking.id,
        reporter_id=actor.id,
        report_type="PRE",
        condition=condition,
        notes=notes,
        photos_json=photos or [],
        checklist_json=checklist or {},
        flagged_for_review=flagged,
    )
    db.add(pre_report)
    db.flush()

    audit_service.write_audit(
        db,
        entity_type="booking",
        entity_id=booking.id,
        action="BOOKING_QR_CHECKIN",
        payload={
            "checked_in_at": str(now),
            "condition": condition,
            "checklist": checklist or {},
            "photos_count": len(photos or []),
            "pre_report_id": pre_report.id,
            "flagged": flagged,
        },
        actor_id=actor.id,
        actor_role=actor.role,
        rationale=f"QR check-in completed with before-condition checklist ({condition}).",
    )

    notification_service.notify(
        db,
        user_id=booking.user_id,
        title="Session Checked In 🚀",
        message=f"Check-in complete for booking #{booking.id}. Machine is now active.",
        notif_type="BOOKING_UPDATE",
        entity_type="booking",
        entity_id=booking.id,
    )

    return booking, pre_report


def perform_qr_checkout(
    db: Session,
    booking_id: int,
    actor: User,
    condition: str = "GOOD",
    checklist: Optional[Dict[str, Any]] = None,
    notes: Optional[str] = None,
    photos: Optional[List[str]] = None,
) -> Tuple[Booking, ConditionReport, Optional[Dict[str, Any]], bool, int]:
    """
    QR-based return/checkout with after-condition checklist, notes, photos,
    advisory photo-diff comparison against pre-session photo, and late return detection.
    Late returns only PROPOSE an overtime penalty; no automated penalty is applied.
    Advisory photo-diff flags anomalies for owner review labeled 'Advisory only — a human decides'.
    """
    booking = _get_booking_or_404(db, booking_id)
    _assert_status(booking, "IN_PROGRESS")

    if actor.role not in ("owner", "manager", "admin") and booking.user_id != actor.id:
        raise HTTPException(status_code=403, detail="Cannot check out for another user's booking.")

    now = app_now()
    is_late = now > booking.slot_end
    overdue_minutes = int((now - booking.slot_end).total_seconds() / 60) if is_late else 0

    equip = db.query(Equipment).filter(Equipment.id == booking.equipment_id).first()

    # Late return handling: propose penalty for human review
    if is_late and overdue_minutes > 5:
        overtime_hours = max(1, int(ceil(overdue_minutes / 60.0)))
        proposed_penalty = overtime_hours * (equip.credit_per_hour if equip else 10)
        rationale = (
            f"Booking #{booking.id} (equipment #{booking.equipment_id}) returned "
            f"{overdue_minutes} minutes after scheduled end ({booking.slot_end} UTC). "
            f"Proposing late return fee of {proposed_penalty} credits for {overtime_hours} overtime hour(s)."
        )
        late_proposal = ActionProposal(
            proposal_type="LATE_RETURN_PENALTY",
            entity_type="booking",
            entity_id=booking.id,
            triggered_by="scheduler",
            rationale=rationale,
            proposed_payload={
                "booking_id": booking.id,
                "user_id": booking.user_id,
                "overdue_minutes": overdue_minutes,
                "proposed_penalty_credits": proposed_penalty,
                "explanation": "Human manager review required before applying late penalty.",
            },
            status="PENDING",
        )
        db.add(late_proposal)
        db.flush()

        audit_service.write_audit(
            db,
            entity_type="booking",
            entity_id=booking.id,
            action="LATE_RETURN_PROPOSAL_CREATED",
            payload={"overdue_minutes": overdue_minutes, "proposed_penalty": proposed_penalty},
            actor_id=None,
            actor_role="system",
            rationale=rationale,
        )

        notification_service.notify(
            db,
            user_id=booking.user_id,
            title="Overdue Return Recorded ⚠️",
            message=f"Session #{booking.id} was returned {overdue_minutes} minutes late. An overtime review has been submitted for lab manager assessment.",
            notif_type="OVERDUE_RETURN",
            entity_type="booking",
            entity_id=booking.id,
        )

    # Advisory photo-diff
    diff_result: Optional[Dict[str, Any]] = None
    pre_report = (
        db.query(ConditionReport)
        .filter(ConditionReport.booking_id == booking.id, ConditionReport.report_type == "PRE")
        .order_by(ConditionReport.created_at.desc())
        .first()
    )

    if pre_report and pre_report.photos_json and photos and len(photos) > 0:
        pre_file = pre_report.photos_json[0]
        post_file = photos[0]
        diff_result = compare_condition_photos(pre_file, post_file)

        if diff_result.get("is_significant"):
            advisory_rationale = (
                f"Advisory visual diff detected {diff_result['change_percentage']}% change "
                f"between pre- and post-condition photos for Booking #{booking.id}. "
                f"Flagged for lab owner inspection. Advisory only — a human decides."
            )
            inspection_proposal = ActionProposal(
                proposal_type="ADVISORY_DAMAGE_INSPECTION",
                entity_type="booking",
                entity_id=booking.id,
                triggered_by="ai_advisory",
                rationale=advisory_rationale,
                proposed_payload={
                    "booking_id": booking.id,
                    "equipment_id": booking.equipment_id,
                    "change_percentage": diff_result["change_percentage"],
                    "diff_photo_filename": diff_result.get("diff_photo_filename"),
                    "advisory_label": "Advisory only — a human decides",
                    "pre_photo": pre_file,
                    "post_photo": post_file,
                },
                status="PENDING",
            )
            db.add(inspection_proposal)
            db.flush()

            audit_service.write_audit(
                db,
                entity_type="booking",
                entity_id=booking.id,
                action="ADVISORY_PHOTO_DIFF_FLAGGED",
                payload={
                    "booking_id": booking.id,
                    "change_percentage": diff_result["change_percentage"],
                    "advisory_label": "Advisory only — a human decides",
                },
                actor_id=None,
                actor_role="ai",
                rationale=advisory_rationale,
            )

    flagged_for_review = bool(
        condition in ("DAMAGED", "BROKEN")
        or (diff_result and diff_result.get("is_significant"))
        or is_late
    )

    post_report = ConditionReport(
        booking_id=booking.id,
        reporter_id=actor.id,
        report_type="POST",
        condition=condition,
        notes=notes,
        photos_json=photos or [],
        checklist_json=checklist or {},
        diff_result=diff_result,
        flagged_for_review=flagged_for_review,
    )
    db.add(post_report)
    db.flush()

    # Finalize booking session
    booking.status = "COMPLETED"
    booking.checked_out_at = now
    booking.credits_charged = booking.credits_held

    user = db.query(User).filter(User.id == booking.user_id).first()
    credit_service.deduct_credits(db, user, booking.credits_charged, booking.id, actor.id)

    audit_service.write_audit(
        db,
        entity_type="booking",
        entity_id=booking.id,
        action="BOOKING_QR_CHECKOUT",
        payload={
            "checked_out_at": str(now),
            "credits_charged": booking.credits_charged,
            "condition": condition,
            "is_late": is_late,
            "overdue_minutes": overdue_minutes,
            "diff_percentage": diff_result.get("change_percentage") if diff_result else None,
            "flagged_for_review": flagged_for_review,
        },
        actor_id=actor.id,
        actor_role=actor.role,
        rationale=f"Session checkout completed ({condition}). Post-report filed.",
    )

    notification_service.notify(
        db,
        user_id=booking.user_id,
        title="Session Completed ✓",
        message=f"Booking #{booking.id} completed. {booking.credits_charged} credits deducted. Thank you for maintaining lab safety!",
        notif_type="BOOKING_UPDATE",
        entity_type="booking",
        entity_id=booking.id,
    )

    return booking, post_report, diff_result, is_late, overdue_minutes


def get_side_by_side_comparison(db: Session, booking_id: int, actor: User) -> Dict[str, Any]:
    """
    Builds a side-by-side condition comparison report (PRE vs POST) for a booking,
    with dynamically generated cryptographic signed URLs for all condition photos
    and the advisory visual diff overlay.
    """
    booking = _get_booking_or_404(db, booking_id)
    if actor.role not in ("owner", "manager", "admin") and booking.user_id != actor.id:
        raise HTTPException(status_code=403, detail="Cannot access condition report for another user's booking.")

    equip = db.query(Equipment).filter(Equipment.id == booking.equipment_id).first()
    lab = db.query(Lab).filter(Lab.id == equip.lab_id).first() if equip else None
    booker = db.query(User).filter(User.id == booking.user_id).first()

    pre_report = (
        db.query(ConditionReport)
        .filter(ConditionReport.booking_id == booking.id, ConditionReport.report_type == "PRE")
        .order_by(ConditionReport.created_at.desc())
        .first()
    )
    post_report = (
        db.query(ConditionReport)
        .filter(ConditionReport.booking_id == booking.id, ConditionReport.report_type == "POST")
        .order_by(ConditionReport.created_at.desc())
        .first()
    )

    now = app_now()
    is_late = bool(
        booking.checked_out_at and booking.checked_out_at > booking.slot_end
        or (booking.status == "IN_PROGRESS" and now > booking.slot_end)
    )
    overdue_minutes = 0
    if is_late:
        end_time = booking.checked_out_at or now
        overdue_minutes = max(0, int((end_time - booking.slot_end).total_seconds() / 60))

    def _format_report(rep: Optional[ConditionReport]) -> Optional[Dict[str, Any]]:
        if not rep:
            return None
        signed_urls = [generate_signed_url(fn) for fn in (rep.photos_json or [])]
        return {
            "id": rep.id,
            "booking_id": rep.booking_id,
            "reporter_id": rep.reporter_id,
            "report_type": rep.report_type,
            "condition": rep.condition,
            "notes": rep.notes,
            "photos_json": rep.photos_json or [],
            "checklist_json": rep.checklist_json or {},
            "signed_photo_urls": signed_urls,
            "diff_result": rep.diff_result,
            "flagged_for_review": rep.flagged_for_review,
            "created_at": rep.created_at,
        }

    formatted_pre = _format_report(pre_report)
    formatted_post = _format_report(post_report)

    diff_result = post_report.diff_result if post_report else None
    signed_diff_url = None
    if diff_result and diff_result.get("diff_photo_filename"):
        signed_diff_url = generate_signed_url(diff_result["diff_photo_filename"])

    return {
        "booking_id": booking.id,
        "equipment_id": booking.equipment_id,
        "equipment_name": equip.name if equip else f"Equipment #{booking.equipment_id}",
        "lab_name": lab.name if lab else "Engineering Lab",
        "user_name": booker.full_name if booker else f"User #{booking.user_id}",
        "slot_start": booking.slot_start,
        "slot_end": booking.slot_end,
        "checked_in_at": booking.checked_in_at,
        "checked_out_at": booking.checked_out_at,
        "is_late": is_late,
        "overdue_minutes": overdue_minutes,
        "status": booking.status,
        "pre_report": formatted_pre,
        "post_report": formatted_post,
        "diff_result": diff_result,
        "signed_diff_photo_url": signed_diff_url,
        "advisory_banner": "Advisory only — a human decides",
        "flagged_for_owner": bool(
            (formatted_post and formatted_post["flagged_for_review"])
            or (formatted_pre and formatted_pre["flagged_for_review"])
            or (diff_result and diff_result.get("is_significant"))
        ),
    }
