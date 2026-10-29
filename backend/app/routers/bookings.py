"""Bookings router — full CRUD + state transitions."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user
from app.models import Booking, ConditionReport, Incident, User
from app.schemas import (
    BookingCreate, BookingManagerAction, BookingOut, CheckoutResponse,
    ConditionReportCreate, ConditionReportOut, IncidentCreate, IncidentOut,
    WaitlistCreate, WaitlistOut,
)
from app.models import Booking, ConditionReport, Incident, User, WaitlistEntry
from app.services import booking_service, waitlist_service
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
    if current_user.role not in ("manager", "admin"):
        raise HTTPException(status_code=403, detail="Manager or admin required.")
    b = booking_service.approve_booking(
        db, booking_id, current_user, payload.note, payload.decision_reason
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
    if current_user.role not in ("manager", "admin"):
        raise HTTPException(status_code=403, detail="Manager or admin required.")
    b = booking_service.reject_booking(
        db, booking_id, current_user, payload.note, payload.decision_reason
    )
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

