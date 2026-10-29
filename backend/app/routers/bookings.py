"""Bookings router — full CRUD + state transitions."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Booking, ConditionReport, Incident, User
from app.schemas import (
    BookingCreate, BookingExtensionRequest, BookingManagerAction, BookingOut, CheckoutResponse,
    ConditionReportCreate, ConditionReportOut, IncidentCreate, IncidentOut,
    ReviewQueueItem, WaitlistCreate, WaitlistOut,
)
from app.models import Booking, ConditionReport, Incident, User, WaitlistEntry
from app.services import booking_service, waitlist_service, notification_service
from app.services.audit_service import write_audit

router = APIRouter(prefix="/bookings", tags=["bookings"])


@router.post("", response_model=BookingOut, status_code=201)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    booking = booking_service.create_booking(
        db, current_user,
        equipment_id=payload.equipment_id,
        slot_start=payload.slot_start,
        slot_end=payload.slot_end,
        purpose=payload.purpose,
        priority_tier=payload.priority_tier,
        group_name=payload.group_name,
        has_supervisor_signoff=payload.has_supervisor_signoff,
        supervisor_name=payload.supervisor_name,
    )
    db.commit()
    db.refresh(booking)
    return booking


@router.get("", response_model=List[BookingOut])
def list_bookings(
    status: Optional[str] = None,
    equipment_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(Booking)
    if current_user.role == "user":
        q = q.filter(Booking.user_id == current_user.id)
    if status:
        q = q.filter(Booking.status == status)
    if equipment_id:
        q = q.filter(Booking.equipment_id == equipment_id)
    return q.order_by(Booking.created_at.desc()).all()


@router.get("/review-queue", response_model=List[ReviewQueueItem])
def get_review_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Review queue for Lab Managers, Owners, and Admins.
    Lists PENDING bookings for labs the user manages or owns,
    complete with the user's booking history, eligibility evaluations,
    prime slot indicators, and waitlist priority scores.
    """
    if current_user.role not in ("owner", "manager", "admin"):
        raise HTTPException(status_code=403, detail="Manager or owner role required to access the review queue.")

    from app.models import Equipment, Lab, LabMembership, UserCredential
    from app.services.allocation_engine import is_prime_slot, compute_waitlist_score
    from app.services.eligibility_engine import evaluate_booking_eligibility
    from app.clock import app_now
    from datetime import timedelta

    now = app_now()

    # Determine which labs the manager/owner oversees
    if current_user.role == "admin":
        allowed_lab_ids = [l.id for l in db.query(Lab.id).all()]
    else:
        memberships = db.query(LabMembership).filter(
            LabMembership.user_id == current_user.id,
            LabMembership.role.in_(["owner", "manager"])
        ).all()
        allowed_lab_ids = [m.lab_id for m in memberships]

    # Query pending bookings for these labs
    pending_bookings = (
        db.query(Booking)
        .join(Equipment, Booking.equipment_id == Equipment.id)
        .filter(
            Booking.status == "PENDING",
            Equipment.lab_id.in_(allowed_lab_ids),
        )
        .order_by(Booking.created_at.asc())
        .all()
    )

    items: List[ReviewQueueItem] = []
    for b in pending_bookings:
        booker = db.query(User).filter(User.id == b.user_id).first()
        equip = db.query(Equipment).filter(Equipment.id == b.equipment_id).first()
        lab = db.query(Lab).filter(Lab.id == equip.lab_id).first()

        # User History
        total_completed = db.query(Booking).filter(
            Booking.user_id == booker.id, Booking.status == "COMPLETED"
        ).count()
        total_no_shows = db.query(Booking).filter(
            Booking.user_id == booker.id, Booking.status == "NO_SHOW"
        ).count()
        seven_days_ago = now - timedelta(days=7)
        recent_bookings = db.query(Booking).filter(
            Booking.user_id == booker.id,
            Booking.status.in_(["COMPLETED", "IN_PROGRESS", "APPROVED"]),
            Booking.slot_start >= seven_days_ago,
        ).all()
        recent_hours = sum((rec.slot_end - rec.slot_start).total_seconds() for rec in recent_bookings) / 3600.0

        user_history = {
            "total_completed_sessions": total_completed,
            "total_no_shows": total_no_shows,
            "strike_count": booker.strike_count,
            "recent_weekly_hours": round(recent_hours, 1),
            "spendable_credits": booker.credit_balance - booker.credit_held,
        }

        # Dynamic Eligibility Check
        user_creds = [
            {"credential_type": c.credential_type, "is_verified": c.is_verified, "expires_at": c.expires_at}
            for c in db.query(UserCredential).filter(UserCredential.user_id == booker.id).all()
        ]
        user_data = {
            "is_active": booker.is_active,
            "strike_count": booker.strike_count,
            "role": booker.role,
            "spendable_credits": booker.credit_balance - booker.credit_held,
            "credentials": user_creds,
        }
        equipment_data = {
            "credit_per_hour": equip.credit_per_hour,
            "deposit_credits": equip.deposit_credits,
            "max_booking_hours": equip.max_booking_hours,
            "required_credentials": equip.required_credentials or [],
            "rules": equip.rules or {},
            "availability_windows": [],
        }
        booking_req = {
            "slot_start": b.slot_start,
            "slot_end": b.slot_end,
            "has_supervisor_signoff": b.has_supervisor_signoff,
            "supervisor_name": b.supervisor_name,
        }
        eval_res = evaluate_booking_eligibility(user_data, equipment_data, booking_req, now)

        # Dynamic Waitlist Score
        score_breakdown = compute_waitlist_score(
            priority_tier=b.priority_tier,
            total_past_completed_bookings=total_completed,
            recent_weekly_hours_used=recent_hours,
            waitlist_created_at=b.created_at,
            evaluation_time=now,
            strike_count=booker.strike_count,
        )

        items.append(
            ReviewQueueItem(
                booking=BookingOut.model_validate(b),
                user_name=booker.full_name,
                user_email=booker.email,
                user_organisation=booker.organisation,
                equipment_name=equip.name,
                lab_name=lab.name,
                lab_id=lab.id,
                user_history=user_history,
                eligibility_evaluation={
                    "is_eligible": eval_res.is_eligible,
                    "reasons_failed": eval_res.reasons_failed,
                    "criteria": [{"rule": r.rule_name, "passed": r.passed, "reason": r.reason} for r in eval_res.results],
                },
                waitlist_score_breakdown=score_breakdown.__dict__,
                is_prime_slot=is_prime_slot(b.slot_start, b.slot_end),
            )
        )

    return items


# ── Waitlist ──────────────────────────────────────────────────────────────────

@router.post("/waitlist", response_model=WaitlistOut, status_code=201)
def add_to_waitlist(
    payload: WaitlistCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    entry = waitlist_service.join_waitlist(
        db=db,
        user=current_user,
        equipment_id=payload.equipment_id,
        desired_start=payload.desired_start,
        desired_end=payload.desired_end,
        purpose=payload.purpose,
        priority_tier=payload.priority_tier,
        group_name=payload.group_name,
    )
    db.commit()
    db.refresh(entry)
    return entry


@router.get("/waitlist", response_model=List[WaitlistOut])
def list_waitlist(
    equipment_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    q = db.query(WaitlistEntry)
    if current_user.role == "user":
        q = q.filter(WaitlistEntry.user_id == current_user.id)
    if equipment_id:
        q = q.filter(WaitlistEntry.equipment_id == equipment_id)
    return q.order_by(WaitlistEntry.ranking_score.desc()).all()


@router.get("/waitlist/{waitlist_id}/why", response_model=dict)
def explain_waitlist_decision(
    waitlist_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Returns the 'Why this outcome?' breakdown for a waitlist placement or promotion.
    """
    entry = db.query(WaitlistEntry).filter(WaitlistEntry.id == waitlist_id).first()
    if not entry:
        raise HTTPException(status_code=404, detail="Waitlist entry not found.")
    if current_user.role == "user" and entry.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")

    return {
        "waitlist_id": entry.id,
        "equipment_id": entry.equipment_id,
        "status": entry.status,
        "ranking_score": entry.ranking_score,
        "score_breakdown": entry.score_breakdown or {},
    }


@router.get("/{booking_id}", response_model=BookingOut)
def get_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    b = db.query(Booking).filter(Booking.id == booking_id).first()
    if not b:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if current_user.role == "user" and b.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Access denied.")
    return b


@router.post("/{booking_id}/approve", response_model=BookingOut)
def approve(
    booking_id: int,
    payload: BookingManagerAction = BookingManagerAction(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("owner", "manager", "admin"):
        raise HTTPException(status_code=403, detail="Manager, owner, or admin required.")
    b = booking_service.approve_booking(
        db, booking_id, current_user, payload.note, payload.decision_reason, override=payload.override
    )
    db.commit()
    db.refresh(b)
    return b


@router.post("/{booking_id}/reject", response_model=BookingOut)
def reject(
    booking_id: int,
    payload: BookingManagerAction = BookingManagerAction(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role not in ("owner", "manager", "admin"):
        raise HTTPException(status_code=403, detail="Manager, owner, or admin required.")
    if not payload.note or not payload.note.strip():
        raise HTTPException(status_code=422, detail="A clear rejection reason is required.")
    b = booking_service.reject_booking(
        db, booking_id, current_user, payload.note, payload.decision_reason
    )
    db.commit()
    db.refresh(b)
    return b


@router.post("/{booking_id}/move-to-waitlist", response_model=WaitlistOut)
def move_booking_to_waitlist(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Manager or owner action: moves a PENDING booking directly to the ranked waitlist
    and releases held credits until an opening occurs.
    """
    if current_user.role not in ("owner", "manager", "admin"):
        raise HTTPException(status_code=403, detail="Manager, owner, or admin required.")

    booking = db.query(Booking).filter(Booking.id == booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")
    if booking.status != "PENDING":
        raise HTTPException(status_code=409, detail=f"Cannot move booking in status '{booking.status}' to waitlist.")

    booker = db.query(User).filter(User.id == booking.user_id).first()

    # Create waitlist entry
    entry = waitlist_service.join_waitlist(
        db=db,
        user=booker,
        equipment_id=booking.equipment_id,
        desired_start=booking.slot_start,
        desired_end=booking.slot_end,
        purpose=booking.purpose,
        priority_tier=booking.priority_tier,
        group_name=booking.group_name,
    )

    # Release held credits and mark booking cancelled/deferred
    booking_service.cancel_booking(db, booking.id, current_user)

    notification_service.notify(
        db,
        user_id=booker.id,
        title="Moved to Waitlist Queue",
        message=f"Your booking #{booking.id} was moved to the waitlist queue (Score: {entry.ranking_score:.1f}). Held credits have been released until a slot frees up.",
        notif_type="WAITLIST_MOVE",
        entity_type="waitlist",
        entity_id=entry.id,
    )
    db.commit()
    db.refresh(entry)
    return entry


@router.post("/{booking_id}/extend", response_model=BookingOut)
def extend(
    booking_id: int,
    payload: BookingExtensionRequest = BookingExtensionRequest(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    b = booking_service.extend_booking(db, booking_id, current_user, extra_hours=payload.extra_hours)
    db.commit()
    db.refresh(b)
    return b


@router.post("/{booking_id}/cancel", response_model=BookingOut)
def cancel(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    b = booking_service.cancel_booking(db, booking_id, current_user)
    db.commit()
    db.refresh(b)
    return b


@router.post("/{booking_id}/checkin", response_model=BookingOut)
def checkin(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    b = booking_service.checkin_booking(db, booking_id, current_user)
    db.commit()
    db.refresh(b)
    return b


@router.post("/{booking_id}/checkout", response_model=CheckoutResponse)
def checkout(
    booking_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    b = booking_service.checkout_booking(db, booking_id, current_user)
    db.commit()
    db.refresh(b)
    user = db.query(User).filter(User.id == b.user_id).first()
    return CheckoutResponse(booking=b, credit_balance_after=user.credit_balance)


# ── Condition Reports ──────────────────────────────────────────────────────────

@router.post("/{booking_id}/condition-reports", response_model=ConditionReportOut, status_code=201)
def file_condition_report(
    booking_id: int,
    payload: ConditionReportCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    report = ConditionReport(
        booking_id=booking_id,
        reporter_id=current_user.id,
        report_type=payload.report_type,
        condition=payload.condition,
        notes=payload.notes,
        photos_json=payload.photos_json,
    )
    db.add(report)
    db.flush()
    write_audit(
        db,
        entity_type="condition_report",
        entity_id=report.id,
        action="CONDITION_REPORT_FILED",
        payload={"booking_id": booking_id, "condition": payload.condition, "type": payload.report_type},
        actor_id=current_user.id,
        actor_role=current_user.role,
    )
    db.commit()
    db.refresh(report)
    return report


# ── Incidents ─────────────────────────────────────────────────────────────────

@router.post("/{booking_id}/incidents", response_model=IncidentOut, status_code=201)
def report_incident(
    booking_id: int,
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    inc = Incident(
        booking_id=booking_id,
        reported_by=current_user.id,
        severity=payload.severity,
        description=payload.description,
        status="OPEN",
    )
    db.add(inc)
    db.flush()
    write_audit(
        db,
        entity_type="incident",
        entity_id=inc.id,
        action="INCIDENT_REPORTED",
        payload={"booking_id": booking_id, "severity": payload.severity},
        actor_id=current_user.id,
        actor_role=current_user.role,
    )
    db.commit()
    db.refresh(inc)
    return inc

