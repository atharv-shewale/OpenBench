"""Credits router."""
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_current_user, get_admin
from app.models import CreditTransaction, User
from app.schemas import AdminCreditGrant, CreditBalance, CreditTransactionOut
from app.services.credit_service import admin_grant

router = APIRouter(prefix="/credits", tags=["credits"])


@router.get("/balance", response_model=CreditBalance)
def get_balance(
    current_user: User = Depends(get_current_user),
):
    return CreditBalance(
        user_id=current_user.id,
        credit_balance=current_user.credit_balance,
        credit_held=current_user.credit_held,
        spendable=current_user.credit_balance - current_user.credit_held,
    )


@router.get("/transactions", response_model=List[CreditTransactionOut])
def list_transactions(
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    target_id = current_user.id
    if current_user.role == "admin" and user_id:
        target_id = user_id
    txs = (
        db.query(CreditTransaction)
        .filter(CreditTransaction.user_id == target_id)
        .order_by(CreditTransaction.created_at.desc())
        .all()
    )
    return txs


@router.post("/grant", response_model=CreditBalance)
def grant_credits(
    payload: AdminCreditGrant,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_admin),
):
    user = db.query(User).filter(User.id == payload.user_id).first()
    if not user:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="User not found.")
    admin_grant(db, user, payload.amount, payload.description or "Admin grant", current_user.id)
    db.commit()
    db.refresh(user)
    return CreditBalance(
        user_id=user.id,
        credit_balance=user.credit_balance,
        credit_held=user.credit_held,
        spendable=user.credit_balance - user.credit_held,
    )

