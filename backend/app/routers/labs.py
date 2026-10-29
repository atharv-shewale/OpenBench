"""Labs router."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_owner_or_above
from app.models import Lab, LabMembership, Equipment
from app.schemas import LabCreate, LabOut, LabOutWithCount
from app.services.audit_service import write_audit

router = APIRouter(prefix="/labs", tags=["labs"])


@router.get("", response_model=List[LabOutWithCount])
def list_labs(
    city: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Lab).filter(Lab.is_active.is_(True))
    if city:
        q = q.filter(Lab.city.ilike(f"%{city}%"))
    if search:
        q = q.filter(
            Lab.name.ilike(f"%{search}%") | Lab.institution.ilike(f"%{search}%")
        )
    labs = q.all()
    result = []
    for lab in labs:
        count = db.query(Equipment).filter(
            Equipment.lab_id == lab.id, Equipment.status == "available"
        ).count()
        d = LabOutWithCount.model_validate(lab)
        d.equipment_count = count
        result.append(d)
    return result


@router.get("/{lab_id}", response_model=LabOut)
def get_lab(lab_id: int, db: Session = Depends(get_db)):
    lab = db.query(Lab).filter(Lab.id == lab_id).first()
    if not lab:
        raise HTTPException(status_code=404, detail="Lab not found.")
    return lab


@router.post("", response_model=LabOut, status_code=201)
def create_lab(
    payload: LabCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_owner_or_above),
):
    lab = Lab(**payload.model_dump())
    db.add(lab)
    db.flush()

    # Auto-assign creator as owner
    membership = LabMembership(user_id=current_user.id, lab_id=lab.id, role="owner")
    db.add(membership)

    write_audit(
        db,
        entity_type="lab",
        entity_id=lab.id,
        action="LAB_CREATED",
        payload=payload.model_dump(),
        actor_id=current_user.id,
        actor_role=current_user.role,
    )
    db.commit()
    db.refresh(lab)
    return lab

