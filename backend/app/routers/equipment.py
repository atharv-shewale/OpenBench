"""Equipment router."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_owner_or_above
from app.models import Equipment, EquipmentAvailabilityWindow, Lab
from app.schemas import EquipmentCreate, EquipmentOut, EquipmentUpdate
from app.services.audit_service import write_audit

router = APIRouter(prefix="/equipment", tags=["equipment"])


def _equip_out(equip: Equipment, db: Session) -> EquipmentOut:
    lab = db.query(Lab).filter(Lab.id == equip.lab_id).first()
    d = EquipmentOut.model_validate(equip)
    d.lab_name = lab.name if lab else None
    return d


@router.get("", response_model=List[EquipmentOut])
def list_equipment(
    lab_id: Optional[int] = None,
    type: Optional[str] = None,
    max_credit_per_hour: Optional[int] = None,
    db: Session = Depends(get_db),
):
    q = db.query(Equipment).filter(Equipment.status == "available")
    if lab_id:
        q = q.filter(Equipment.lab_id == lab_id)
    if type:
        q = q.filter(Equipment.type == type)
    if max_credit_per_hour is not None:
        q = q.filter(Equipment.credit_per_hour <= max_credit_per_hour)
    return [_equip_out(e, db) for e in q.all()]


@router.get("/{equipment_id}", response_model=EquipmentOut)
def get_equipment(equipment_id: int, db: Session = Depends(get_db)):
    equip = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found.")
    return _equip_out(equip, db)


@router.post("", response_model=EquipmentOut, status_code=201)
def create_equipment(
    payload: EquipmentCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_owner_or_above),
):
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
    current_user=Depends(get_owner_or_above),
):
    equip = db.query(Equipment).filter(Equipment.id == equipment_id).first()
    if not equip:
        raise HTTPException(status_code=404, detail="Equipment not found.")

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

