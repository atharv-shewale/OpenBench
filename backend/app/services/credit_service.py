"""
Credit service — all credit mutations go through here.

Invariants enforced:
- credit_balance >= 0 at all times
- credit_held >= 0 at all times
- spendable = credit_balance - credit_held >= 0 before any new hold

Every credit change is mirrored in the credit_transactions ledger (append-only)
and in the audit_log via write_audit().
"""
from __future__ import annotations

from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import CreditTransaction, User
from app.services.audit_service import write_audit


def _record_tx(
    db: Session,
    user: User,
    tx_type: str,
    amount: int,
    booking_id: Optional[int] = None,
    description: Optional[str] = None,
) -> CreditTransaction:
    tx = CreditTransaction(
        user_id=user.id,
        booking_id=booking_id,
        tx_type=tx_type,
        amount=amount,
        balance_after=user.credit_balance,
        description=description,
    )
    db.add(tx)
    db.flush()
    return tx


def welcome_grant(db: Session, user: User, amount: int = 50) -> None:
    """Grant welcome credits on registration."""
    user.credit_balance += amount
    tx = _record_tx(db, user, "WELCOME_GRANT", amount, description=f"Welcome grant: {amount} credits")
    write_audit(
        db,
        entity_type="user",
        entity_id=user.id,
        action="CREDIT_WELCOME_GRANT",
        payload={"amount": amount, "balance_after": user.credit_balance},
        actor_id=None,
        actor_role="system",
    )


def hold_credits(db: Session, user: User, amount: int, booking_id: int) -> None:
    """Reserve credits when a booking is created (not deducted yet)."""
    spendable = user.credit_balance - user.credit_held
    if spendable < amount:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"Insufficient spendable credits. Need {amount}, have {spendable}.",
        )
    user.credit_held += amount
    _record_tx(db, user, "HOLD", amount, booking_id=booking_id, description=f"Hold for booking #{booking_id}")
    write_audit(
        db,
        entity_type="credit_tx",
        entity_id=booking_id,
        action="CREDIT_HELD",
        payload={"amount": amount, "booking_id": booking_id, "held_after": user.credit_held},
        actor_id=user.id,
        actor_role=user.role,
    )


def release_hold(db: Session, user: User, amount: int, booking_id: int) -> None:
    """Release held credits when a booking is cancelled or rejected."""
    user.credit_held = max(0, user.credit_held - amount)
    _record_tx(db, user, "HOLD_RELEASE", amount, booking_id=booking_id,
               description=f"Hold released for booking #{booking_id}")
    write_audit(
        db,
        entity_type="credit_tx",
        entity_id=booking_id,
        action="CREDIT_HOLD_RELEASED",
        payload={"amount": amount, "booking_id": booking_id, "held_after": user.credit_held},
        actor_id=None,
        actor_role="system",
    )


def deduct_credits(
    db: Session, user: User, amount: int, booking_id: int, actor_id: Optional[int] = None
) -> None:
    """Deduct credits on booking COMPLETED. Releases the hold simultaneously."""
    if user.credit_balance < amount:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Insufficient credits for checkout.",
        )
    user.credit_balance -= amount
    user.credit_held = max(0, user.credit_held - amount)
    _record_tx(db, user, "DEDUCT", -amount, booking_id=booking_id,
               description=f"Deducted for completed booking #{booking_id}")
    write_audit(
        db,
        entity_type="credit_tx",
        entity_id=booking_id,
        action="CREDIT_DEDUCTED",
        payload={"amount": amount, "booking_id": booking_id, "balance_after": user.credit_balance},
        actor_id=actor_id,
        actor_role=user.role,
    )


def forfeit_credits(
    db: Session, user: User, amount: int, booking_id: int, actor_id: Optional[int], actor_role: str
) -> None:
    """Forfeit held credits on NO_SHOW confirmation."""
    user.credit_balance = max(0, user.credit_balance - amount)
    user.credit_held = max(0, user.credit_held - amount)
    _record_tx(db, user, "FORFEIT", -amount, booking_id=booking_id,
               description=f"Forfeited for no-show booking #{booking_id}")
    write_audit(
        db,
        entity_type="credit_tx",
        entity_id=booking_id,
        action="CREDIT_FORFEITED",
        payload={"amount": amount, "booking_id": booking_id, "balance_after": user.credit_balance},
        actor_id=actor_id,
        actor_role=actor_role,
        rationale=f"No-show penalty confirmed for booking #{booking_id}.",
    )


def admin_grant(
    db: Session, user: User, amount: int, description: str, actor_id: int
) -> None:
    """Admin manually grants credits."""
    user.credit_balance += amount
    _record_tx(db, user, "ADMIN_GRANT", amount, description=description)
    write_audit(
        db,
        entity_type="user",
        entity_id=user.id,
        action="CREDIT_ADMIN_GRANT",
        payload={"amount": amount, "balance_after": user.credit_balance, "description": description},
        actor_id=actor_id,
        actor_role="admin",
    )

