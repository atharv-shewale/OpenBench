"""Equipment router with search, filtering, QR code generator, and eligibility checking."""
import io
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import qrcode

from app.clock import app_now
from app.database import get_db
from app.dependencies import get_current_user, get_owner_or_above, get_any_authenticated
from app.models import (
    Booking,
    Equipment,
    EquipmentAvailabilityWindow,
    Lab,
    LabMembership,
    User,
    UserCredential,
)
from app.schemas import (
    EligibilityCheckResponse,
    EligibilityCriterion,
    EquipmentCreate,
    EquipmentOut,
    EquipmentUpdate,
    UsageSignalPayload,
    UsageSignalResponse,
)
from app.services.audit_service import write_audit

router = APIRouter(prefix="/equipment", tags=["equipment"])


def _equip_out(equip: Equipment, db: Session) -> EquipmentOut:
    lab = db.query(Lab).filter(Lab.id == equip.lab_id).first()
    approver = db.query(User).filter(User.id == equip.approver_id).first() if equip.approver_id else None
    d = EquipmentOut.model_validate(equip)
    d.lab_name = lab.name if lab else None
    d.institution = lab.institution if lab else None
    d.city = lab.city if lab else None
    d.approver_name = approver.full_name if approver else None
    return d


@router.get("", response_model=List[EquipmentOut])
def list_equipment(
    search: Optional[str] = None,
    category: Optional[str] = None,
    location: Optional[str] = None,
    city: Optional[str] = None,
    lab_id: Optional[int] = None,
    available_only: bool = True,
    max_credit_per_hour: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Equipment).join(Lab, Equipment.lab_id == Lab.id)
    if available_only:
        q = q.filter(Equipment.status == "available")
    if category:
        q = q.filter(Equipment.type == category)
    if lab_id:
        q = q.filter(Equipment.lab_id == lab_id)
    if city:
        q = q.filter(Lab.city.ilike(f"%{city}%"))
    if location:
        q = q.filter(
            (Equipment.location.ilike(f"%{location}%")) |
            (Lab.city.ilike(f"%{location}%")) |
            (Lab.name.ilike(f"%{location}%"))
        )
    if search:
        search_filter = (
            Equipment.name.ilike(f"%{search}%") |
            Equipment.description.ilike(f"%{search}%") |
            Lab.name.ilike(f"%{search}%") |
            Lab.institution.ilike(f"%{search}%")
        )
        q = q.filter(search_filter)
    if max_credit_per_hour is not None:
        q = q.filter(Equipment.credit_per_hour <= max_credit_per_hour)

    items = q.all()
    return [_equip_out(e, db) for e in items]


@router.get("/{equipment_id}", response_model=EquipmentOut)
def get_equipment(equipment_id: int, db: Session = Depends(get_db)):
    equip = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found.")
    return _equip_out(equip, db)


@router.get("/{equipment_id}/eligibility", response_model=EligibilityCheckResponse)
def check_eligibility(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_any_authenticated),
):
    """
    Evaluates whether the authenticated user is currently eligible to book this resource:
    1. Account is active
    2. Strikes < 3 (not suspended)
    3. Spendable credits >= credit_per_hour + deposit_credits
    4. Holds all active, non-expired required credentials
    """
    equip = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found.")

    criteria: List[EligibilityCriterion] = []
    reasons: List[str] = []
    is_eligible = True

    # 1. Active account
    if current_user.is_active:
        criteria.append(EligibilityCriterion(
            criterion="Account Status", met=True, details="Account is active and verified."
        ))
    else:
        is_eligible = False
        reasons.append("Your account has been deactivated.")
        criteria.append(EligibilityCriterion(
            criterion="Account Status", met=False, details="Account is deactivated."
        ))

    # 2. Strike limit
    if current_user.strike_count < 3:
        criteria.append(EligibilityCriterion(
            criterion="Disciplinary Record",
            met=True,
            details=f"{current_user.strike_count}/3 strikes on record."
        ))
    else:
        is_eligible = False
        reasons.append(f"Account has reached {current_user.strike_count} strikes (limit: 3).")
        criteria.append(EligibilityCriterion(
            criterion="Disciplinary Record",
            met=False,
            details=f"Account suspended due to {current_user.strike_count} strikes."
        ))

    # 3. Credits
    spendable = current_user.credit_balance - current_user.credit_held
    min_required = equip.credit_per_hour + equip.deposit_credits
    if spendable >= min_required:
        criteria.append(EligibilityCriterion(
            criterion="Credit Balance",
            met=True,
            details=f"Spendable credits ({spendable}) cover minimum 1 hr + deposit ({min_required})."
        ))
    else:
        is_eligible = False
        reasons.append(f"Insufficient spendable credits: need at least {min_required}, you currently have {spendable}.")
        criteria.append(EligibilityCriterion(
            criterion="Credit Balance",
            met=False,
            details=f"Spendable: {spendable} cr. Required: {min_required} cr ({equip.credit_per_hour}/hr + {equip.deposit_credits} deposit)."
        ))

    # 4. Required credentials check
    req_creds = equip.required_credentials or []
    if not req_creds:
        criteria.append(EligibilityCriterion(
            criterion="Required Certifications",
            met=True,
            details="No specialized certifications required for this resource."
        ))
    else:
        now = app_now()
        user_creds = db.query(UserCredential).filter(
            UserCredential.user_id == current_user.id,
            UserCredential.is_verified.is_(True),
            (UserCredential.expires_at.is_(None)) | (UserCredential.expires_at > now),
        ).all()
        held_types = {c.credential_type for c in user_creds}

        for cred in req_creds:
            if cred in held_types:
                criteria.append(EligibilityCriterion(
                    criterion=f"Certification: {cred}",
                    met=True,
                    details="Verified and active certification on file."
                ))
            else:
                is_eligible = False
                reasons.append(f"Missing required certification: {cred}")
                criteria.append(EligibilityCriterion(
                    criterion=f"Certification: {cred}",
                    met=False,
                    details=f"You do not possess an active, verified {cred} certification."
                ))

    # 5. Resource operational status
    if equip.status == "available":
        criteria.append(EligibilityCriterion(
            criterion="Equipment Availability",
            met=True,
            details="Equipment is currently active and accepting bookings."
        ))
    else:
        is_eligible = False
        reasons.append(f"Equipment is currently in '{equip.status}' status.")
        criteria.append(EligibilityCriterion(
            criterion="Equipment Availability",
            met=False,
            details=f"Resource is marked as {equip.status}."
        ))

    return EligibilityCheckResponse(
        equipment_id=equipment_id,
        is_eligible=is_eligible,
        reasons=reasons,
        criteria=criteria,
        user_balance=spendable,
        required_credits=equip.credit_per_hour,
        deposit_credits=equip.deposit_credits,
    )


@router.get("/{equipment_id}/qr")
def get_equipment_qr(equipment_id: int, db: Session = Depends(get_db)):
    """Generate and return a PNG QR code linking to the equipment page / check-in code."""
    equip = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found.")

    payload = f"openbench://equipment/{equip.id}"
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=3,
    )
    qr.add_data(payload)
    qr.make(fit=True)

    img = qr.make_image(fill_color="#1d4ed8", back_color="white")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)

    return StreamingResponse(buf, media_type="image/png")


# ── Owner / Manager CRUD ───────────────────────────────────────────────────────

@router.post("", response_model=EquipmentOut, status_code=201)
def create_equipment(
    payload: EquipmentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_owner_or_above),
):
    if current_user.role != "admin":
        membership = db.query(LabMembership).filter(
            LabMembership.user_id == current_user.id,
            LabMembership.lab_id == payload.lab_id,
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="You do not manage or own this lab.")

    data = payload.model_dump(exclude={"availability_windows"})
    equip = Equipment(**data)
    db.add(equip)
    db.flush()

    for w in payload.availability_windows:
        db.add(EquipmentAvailabilityWindow(equipment_id=equip.id, **w.model_dump()))

    write_audit(
        db,
        entity_type="equipment",
        entity_id=equip.id,
        action="EQUIPMENT_CREATED",
        payload=data,
        actor_id=current_user.id,
        actor_role=current_user.role,
    )
    db.commit()
    db.refresh(equip)
    return _equip_out(equip, db)


@router.patch("/{equipment_id}", response_model=EquipmentOut)
def update_equipment(
    equipment_id: int,
    payload: EquipmentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_owner_or_above),
):
    equip = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found.")

    if current_user.role != "admin":
        membership = db.query(LabMembership).filter(
            LabMembership.user_id == current_user.id,
            LabMembership.lab_id == equip.lab_id,
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="You do not manage this lab's equipment.")

    update_data = payload.model_dump(exclude_unset=True, exclude={"availability_windows"})
    for k, v in update_data.items():
        setattr(equip, k, v)

    if payload.availability_windows is not None:
        db.query(EquipmentAvailabilityWindow).filter(
            EquipmentAvailabilityWindow.equipment_id == equipment_id
        ).delete()
        for w in payload.availability_windows:
            db.add(EquipmentAvailabilityWindow(equipment_id=equip.id, **w.model_dump()))

    write_audit(
        db,
        entity_type="equipment",
        entity_id=equip.id,
        action="EQUIPMENT_UPDATED",
        payload=update_data,
        actor_id=current_user.id,
        actor_role=current_user.role,
    )
    db.commit()
    db.refresh(equip)
    return _equip_out(equip, db)


@router.delete("/{equipment_id}", status_code=200)
def delete_equipment(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_owner_or_above),
):
    equip = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found.")

    if current_user.role != "admin":
        membership = db.query(LabMembership).filter(
            LabMembership.user_id == current_user.id,
            LabMembership.lab_id == equip.lab_id,
            LabMembership.role.in_(["owner", "manager"])
        ).first()
        if not membership:
            raise HTTPException(status_code=403, detail="You do not have permission to delete equipment in this lab.")

    write_audit(
        db,
        entity_type="equipment",
        entity_id=equip.id,
        action="EQUIPMENT_DELETED",
        payload={"name": equip.name, "lab_id": equip.lab_id},
        actor_id=current_user.id,
        actor_role=current_user.role,
    )
    db.delete(equip)
    db.commit()
    return {"message": f"Equipment #{equipment_id} removed."}


# ── Telemetry & Usage Signal (Machine Simulator) ──────────────────────────────

@router.post("/{equipment_id}/usage-signal", response_model=UsageSignalResponse)
def emit_usage_signal(
    equipment_id: int,
    payload: UsageSignalPayload = UsageSignalPayload(),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_any_authenticated),
):
    """
    Usage signal / IoT telemetry heartbeat endpoint.
    Used by physical equipment sensors or the Machine Simulator panel.
    Clearly labelled as simulated in telemetry payload and audit trail.
    Updates the equipment and any active booking, preventing false no-show auto-releases.
    """
    equip = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found.")

    now = app_now()
    equip.last_usage_signal_at = now
    equip.current_telemetry = {
        **payload.model_dump(),
        "reported_at": now.isoformat(),
        "actor_id": current_user.id,
    }

    # Find active or approved booking in current window
    active_booking = (
        db.query(Booking)
        .filter(
            Booking.equipment_id == equipment_id,
            Booking.status.in_(["APPROVED", "IN_PROGRESS"]),
            Booking.slot_start <= now,
            Booking.slot_end >= now,
        )
        .first()
    )

    if active_booking:
        active_booking.last_usage_signal_at = now

    write_audit(
        db,
        entity_type="equipment",
        entity_id=equip.id,
        action="USAGE_SIGNAL_RECORDED",
        payload={
            "power_watts": payload.power_watts,
            "is_active": payload.is_active,
            "activity_type": payload.activity_type,
            "simulated": payload.simulated,
            "active_booking_id": active_booking.id if active_booking else None,
        },
        actor_id=current_user.id,
        actor_role=current_user.role,
        rationale=f"Usage signal emitted (Simulated: {payload.simulated}). Activity: {payload.activity_type}.",
    )
    db.commit()
    db.refresh(equip)

    return UsageSignalResponse(
        equipment_id=equip.id,
        signal_received_at=now,
        is_active=payload.is_active,
        active_booking_id=active_booking.id if active_booking else None,
        simulated=payload.simulated,
        message=f"Usage signal processed for {equip.name}. Active telemetry verified (Simulated: {payload.simulated}).",
    )


@router.get("/{equipment_id}/telemetry", response_model=dict)
def get_equipment_telemetry(
    equipment_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_any_authenticated),
):
    """Returns the latest telemetry heartbeat and simulated machine state."""
    equip = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found.")

    return {
        "equipment_id": equip.id,
        "name": equip.name,
        "last_usage_signal_at": equip.last_usage_signal_at,
        "current_telemetry": equip.current_telemetry or {
            "is_active": False,
            "power_watts": 0.0,
            "simulated": True,
            "activity_type": "idle",
        },
        "simulated": True,
    }
