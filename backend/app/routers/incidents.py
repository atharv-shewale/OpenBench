"""
Incidents router — damage, delay, dispute, and safety incident reporting,
tracking, evidence attachment, and human resolution.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.clock import app_now
from app.database import get_db
from app.dependencies import get_any_authenticated, get_current_user, get_manager_or_admin
from app.models import Booking, Incident, User
from app.schemas import IncidentCreate, IncidentOut, IncidentResolveRequest
from app.services import audit_service, notification_service

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("", response_model=IncidentOut, status_code=201)
def report_incident(
    payload: IncidentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_any_authenticated),
):
    """
    Files an incident (damage, delay, dispute, or safety concern)
    associated with a booking, with severity rating and evidence URLs.
    """
    booking = db.query(Booking).filter(Booking.id == payload.booking_id).first()
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found.")

    if current_user.role == "user" and booking.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Cannot file incident for another user's booking.")

    inc = Incident(
        booking_id=payload.booking_id,
        reported_by=current_user.id,
        incident_type=payload.incident_type,
        severity=payload.severity,
        description=payload.description,
        evidence_json=payload.evidence_json or [],
        status="OPEN",
    )
    db.add(inc)
    db.flush()

    audit_service.write_audit(
        db,
        entity_type="incident",
        entity_id=inc.id,
        action="INCIDENT_REPORTED",
        payload={
            "booking_id": payload.booking_id,
            "incident_type": payload.incident_type,
            "severity": payload.severity,
            "description": payload.description,
            "evidence_count": len(payload.evidence_json or []),
        },
        actor_id=current_user.id,
        actor_role=current_user.role,
        rationale=f"Incident filed ({payload.incident_type}, {payload.severity}): {payload.description}",
    )
    db.commit()
    db.refresh(inc)
    return inc


@router.get("", response_model=List[IncidentOut])
def list_incidents(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    incident_type: Optional[str] = None,
    booking_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_any_authenticated),
):
    """
    Lists incidents. Regular users only see incidents tied to their own bookings.
    Managers, owners, and admins can query across all labs.
    """
    q = db.query(Incident)
    if current_user.role == "user":
        q = q.join(Booking, Incident.booking_id == Booking.id).filter(Booking.user_id == current_user.id)
    if status:
        q = q.filter(Incident.status == status)
    if severity:
        q = q.filter(Incident.severity == severity)
    if incident_type:
        q = q.filter(Incident.incident_type == incident_type)
    if booking_id:
        q = q.filter(Incident.booking_id == booking_id)

    return q.order_by(Incident.created_at.desc()).all()


@router.post("/{incident_id}/resolve", response_model=IncidentOut)
def resolve_incident(
    incident_id: int,
    payload: IncidentResolveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_manager_or_admin),
):
    """
    Manager or admin resolution for an incident.
    Records resolution notes, sets status to RESOLVED, and logs to audit ledger.
    """
    inc = db.query(Incident).filter(Incident.id == incident_id).first()
    if not inc:
        raise HTTPException(status_code=404, detail="Incident not found.")
    if inc.status == "RESOLVED":
        raise HTTPException(status_code=409, detail="Incident is already resolved.")

    now = app_now()
    inc.status = "RESOLVED"
    inc.resolution = payload.resolution
    inc.resolved_by = current_user.id
    inc.resolved_at = now

    booking = db.query(Booking).filter(Booking.id == inc.booking_id).first()

    audit_service.write_audit(
        db,
        entity_type="incident",
        entity_id=inc.id,
        action="INCIDENT_RESOLVED",
        payload={"resolution": payload.resolution, "resolver_id": current_user.id},
        actor_id=current_user.id,
        actor_role=current_user.role,
        rationale=f"Incident #{inc.id} resolved by {current_user.full_name}: {payload.resolution}",
    )

    if booking:
        notification_service.notify(
            db,
            user_id=booking.user_id,
            title="Incident Resolved ✓",
            message=f"Incident #{inc.id} ({inc.incident_type}) for booking #{booking.id} has been resolved: {payload.resolution}",
            notif_type="BOOKING_UPDATE",
            entity_type="incident",
            entity_id=inc.id,
        )

    db.commit()
    db.refresh(inc)
    return inc

