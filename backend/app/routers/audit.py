"""Audit log router — query, verify, and export the hash chain."""
import csv
import io
from typing import Optional
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_manager_or_admin
from app.models import AuditLog
from app.schemas import AuditLogOut, AuditPage, ChainVerifyResult
from app.services.audit_service import verify_chain

router = APIRouter(prefix="/audit", tags=["audit"])


@router.get("", response_model=AuditPage)
def query_audit(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    action: Optional[str] = None,
    actor_id: Optional[int] = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, le=100),
    db: Session = Depends(get_db),
    current_user=Depends(get_manager_or_admin),
):
    q = db.query(AuditLog)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        q = q.filter(AuditLog.entity_id == entity_id)
    if action:
        q = q.filter(AuditLog.action.ilike(f"%{action}%"))
    if actor_id is not None:
        q = q.filter(AuditLog.actor_id == actor_id)

    total = q.count()
    items = q.order_by(AuditLog.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    return AuditPage(total=total, page=page, page_size=page_size, items=items)


@router.get("/verify", response_model=ChainVerifyResult)
@router.post("/verify", response_model=ChainVerifyResult)
def verify(db: Session = Depends(get_db), current_user=Depends(get_manager_or_admin)):
    return verify_chain(db)


@router.get("/export.csv")
def export_audit_csv(
    entity_type: Optional[str] = None,
    entity_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_manager_or_admin),
):
    """
    Exports the hash-chained audit ledger as an immutable CSV record.
    """
    q = db.query(AuditLog)
    if entity_type:
        q = q.filter(AuditLog.entity_type == entity_type)
    if entity_id is not None:
        q = q.filter(AuditLog.entity_id == entity_id)

    entries = q.order_by(AuditLog.id.asc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "id", "timestamp", "entity_type", "entity_id", "action",
        "actor_id", "actor_role", "rationale", "prev_hash", "hash",
    ])
    for e in entries:
        writer.writerow([
            e.id,
            e.created_at.isoformat() if e.created_at else "",
            e.entity_type,
            e.entity_id,
            e.action,
            e.actor_id or "",
            e.actor_role or "",
            e.rationale or "",
            e.prev_hash,
            e.hash,
        ])

    return Response(
        content=output.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=openbench_audit_ledger.csv"},
    )

