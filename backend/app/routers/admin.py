"""Admin router — users, clock, seed."""
from typing import List, Optional
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import clock as demo_clock
from app.database import get_db
from app.dependencies import get_admin, get_manager_or_admin
from app.models import LabMembership, User
from app.schemas import (
    ClockAdvance, ClockState, LabMembershipCreate,
    UserOut, UserUpdateAdmin,
)
from app.services.audit_service import write_audit

router = APIRouter(prefix="/admin", tags=["admin"])


# ── Users ──────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=List[UserOut])
def list_users(
    role: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db),
    _=Depends(get_admin),
):
    q = db.query(User)
    if role:
        q = q.filter(User.role == role)
    if search:
        q = q.filter(User.full_name.ilike(f"%{search}%") | User.email.ilike(f"%{search}%"))
    return q.all()


@router.get("/users/{user_id}", response_model=UserOut)
def get_user(user_id: int, db: Session = Depends(get_db), _=Depends(get_admin)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
    return user


@router.patch("/users/{user_id}", response_model=UserOut)
def update_user(
    user_id: int,
    payload: UserUpdateAdmin,
    db: Session = Depends(get_db),
    current_user=Depends(get_admin),
):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")

    old_role = user.role
    for k, v in payload.model_dump(exclude_unset=True).items():
        setattr(user, k, v)

    write_audit(
        db,
        entity_type="user",
        entity_id=user.id,
        action="USER_UPDATED",
        payload={"changes": payload.model_dump(exclude_unset=True), "old_role": old_role},
        actor_id=current_user.id,
        actor_role=current_user.role,
    )
    db.commit()
    db.refresh(user)
    return user


@router.post("/users/{user_id}/lab-membership", status_code=201)
def assign_lab_membership(
    user_id: int,
    payload: LabMembershipCreate,
    db: Session = Depends(get_db),
    current_user=Depends(get_admin),
):
    existing = db.query(LabMembership).filter(
        LabMembership.user_id == user_id, LabMembership.lab_id == payload.lab_id
    ).first()
    if existing:
        existing.role = payload.role
    else:
        db.add(LabMembership(user_id=user_id, lab_id=payload.lab_id, role=payload.role))

    write_audit(
        db,
        entity_type="user",
        entity_id=user_id,
        action="LAB_MEMBERSHIP_ASSIGNED",
        payload={"lab_id": payload.lab_id, "role": payload.role},
        actor_id=current_user.id,
        actor_role=current_user.role,
    )
    db.commit()
    return {"message": "Membership assigned."}


# ── Demo Clock ─────────────────────────────────────────────────────────────────

@router.get("/clock", response_model=ClockState)
def get_clock(_=Depends(get_manager_or_admin)):
    real = datetime.now(timezone.utc).replace(tzinfo=None)
    return ClockState(
        real_utc=real,
        app_now=demo_clock.app_now(),
        offset_seconds=demo_clock.get_offset(),
    )


@router.post("/clock/advance", response_model=ClockState)
def advance_clock(
    payload: ClockAdvance,
    db: Session = Depends(get_db),
    current_user=Depends(get_manager_or_admin),
):
    new_offset = demo_clock.advance_clock(payload.seconds)
    write_audit(
        db,
        entity_type="clock",
        entity_id=0,
        action="CLOCK_ADVANCED",
        payload={"seconds_advanced": payload.seconds, "new_offset": new_offset},
        actor_id=current_user.id,
        actor_role=current_user.role,
        rationale=f"Demo clock advanced by {payload.seconds}s by {current_user.role} ({current_user.full_name}).",
    )
    db.commit()
    real = datetime.now(timezone.utc).replace(tzinfo=None)
    return ClockState(real_utc=real, app_now=demo_clock.app_now(), offset_seconds=new_offset)


@router.post("/clock/reset", response_model=ClockState)
def reset_clock(db: Session = Depends(get_db), current_user=Depends(get_manager_or_admin)):
    demo_clock.reset_clock()
    write_audit(
        db,
        entity_type="clock",
        entity_id=0,
        action="CLOCK_RESET",
        payload={"new_offset": 0},
        actor_id=current_user.id,
        actor_role=current_user.role,
        rationale=f"Demo clock reset to real UTC by {current_user.role} ({current_user.full_name}).",
    )
    db.commit()
    real = datetime.now(timezone.utc).replace(tzinfo=None)
    return ClockState(real_utc=real, app_now=demo_clock.app_now(), offset_seconds=0)


# ── Seed ───────────────────────────────────────────────────────────────────────

@router.post("/seed")
def seed_data(
    wipe: bool = False,
    db: Session = Depends(get_db),
    _=Depends(get_admin),
):
    from app.seed import run_seed  # lazy import to avoid circular deps
    result = run_seed(db, wipe=wipe)
    return result

