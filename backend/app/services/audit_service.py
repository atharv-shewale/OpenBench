"""
Audit service — append-only, hash-chained audit log.

Rules:
1. Never UPDATE or DELETE from audit_log.
2. Every write calls app_now() for the timestamp.
3. Each entry's hash covers its own data + the previous entry's hash.
4. verify_chain() walks every entry in order to validate integrity.
"""
from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.clock import app_now
from app.models import AuditLog

GENESIS_PREV_HASH = "0" * 64


def _compute_hash(
    row_id: int,
    entity_type: str,
    entity_id: int,
    action: str,
    payload: Dict[str, Any],
    prev_hash: str,
) -> str:
    """Deterministic SHA-256 over the row's identity fields."""
    payload_str = json.dumps(payload, sort_keys=True, default=str)
    raw = f"{row_id}|{entity_type}|{entity_id}|{action}|{payload_str}|{prev_hash}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def write_audit(
    db: Session,
    *,
    entity_type: str,
    entity_id: int,
    action: str,
    payload: Dict[str, Any],
    actor_id: Optional[int] = None,
    actor_role: Optional[str] = None,
    rationale: Optional[str] = None,
) -> AuditLog:
    """
    Append one entry to the audit log with a valid hash chain.

    The caller is responsible for calling db.commit() (or flushing inside
    a larger transaction) after this function returns.
    """
    # Fetch the previous entry's hash (or genesis)
    last = db.query(AuditLog).order_by(AuditLog.id.desc()).first()
    prev_hash = last.hash if last else GENESIS_PREV_HASH

    entry = AuditLog(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        actor_id=actor_id,
        actor_role=actor_role,
        payload=payload,
        rationale=rationale,
        prev_hash=prev_hash,
        hash="__pending__",   # placeholder; filled in after flush gives us the id
        created_at=app_now(),
    )
    db.add(entry)
    db.flush()  # assigns entry.id without committing the outer transaction

    real_hash = _compute_hash(
        entry.id, entity_type, entity_id, action, payload, prev_hash
    )
    entry.hash = real_hash
    db.flush()

    return entry


def verify_chain(db: Session) -> Dict[str, Any]:
    """
    Walk every audit_log row in ID order and verify the hash chain.
    Returns a dict compatible with the ChainVerifyResult schema.
    """
    entries = db.query(AuditLog).order_by(AuditLog.id.asc()).all()
    if not entries:
        return {"chain_valid": True, "total_entries": 0}

    expected_prev = GENESIS_PREV_HASH

    for entry in entries:
        # 1. Check prev_hash linkage
        if entry.prev_hash != expected_prev:
            return {
                "chain_valid": False,
                "total_entries": len(entries),
                "broken_at_id": entry.id,
                "first_entry_id": entries[0].id,
                "last_entry_id": entries[-1].id,
            }
        # 2. Recompute and verify the row's own hash
        expected_hash = _compute_hash(
            entry.id, entry.entity_type, entry.entity_id,
            entry.action, entry.payload, entry.prev_hash,
        )
        if entry.hash != expected_hash:
            return {
                "chain_valid": False,
                "total_entries": len(entries),
                "broken_at_id": entry.id,
                "first_entry_id": entries[0].id,
                "last_entry_id": entries[-1].id,
            }
        expected_prev = entry.hash

    return {
        "chain_valid": True,
        "total_entries": len(entries),
        "first_entry_id": entries[0].id,
        "last_entry_id": entries[-1].id,
    }

