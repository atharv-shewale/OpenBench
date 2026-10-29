"""Proposals router — human-in-the-loop review of automated actions."""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.dependencies import get_manager_or_admin, get_any_authenticated
from app.models import ActionProposal, Booking, Strike, User
from app.schemas import ProposalOut, ProposalReviewAction, ProposalContestRequest
from app.services import audit_service, credit_service, notification_service
from app.services.auto_release_service import contest_proposal as svc_contest_proposal
from app.clock import app_now

router = APIRouter(prefix="/proposals", tags=["proposals"])


@router.get("", response_model=List[ProposalOut])
def list_proposals(
    status: Optional[str] = "PENDING",
    proposal_type: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user=Depends(get_manager_or_admin),
):
    q = db.query(ActionProposal)
    if status and status != "ALL":
        q = q.filter(ActionProposal.status == status)
    if proposal_type:
        q = q.filter(ActionProposal.proposal_type == proposal_type)
    return q.order_by(ActionProposal.created_at.desc()).all()


@router.get("/my-proposals", response_model=List[ProposalOut])
def list_my_proposals(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_any_authenticated),
):
    """Returns proposals that directly affect the logged-in user (e.g. proposed strikes)."""
    return (
        db.query(ActionProposal)
        .filter(
            ActionProposal.entity_type == "user",
            ActionProposal.entity_id == current_user.id,
        )
        .order_by(ActionProposal.created_at.desc())
        .all()
    )


@router.get("/{proposal_id}", response_model=ProposalOut)
def get_proposal(
    proposal_id: int,
    db: Session = Depends(get_db),
    current_user=Depends(get_manager_or_admin),
):
    p = db.query(ActionProposal).filter(ActionProposal.id == proposal_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    return p


@router.post("/{proposal_id}/contest", response_model=ProposalOut)
def contest_action_proposal(
    proposal_id: int,
    payload: ProposalContestRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_any_authenticated),
):
    """Allows a user to contest a proposed strike or penalty with an explanation."""
    return svc_contest_proposal(db, proposal_id, current_user, payload.contestation_note)


@router.post("/{proposal_id}/confirm", response_model=ProposalOut)
def confirm_proposal(
    proposal_id: int,
    payload: ProposalReviewAction = ProposalReviewAction(),
    db: Session = Depends(get_db),
    current_user=Depends(get_manager_or_admin),
):
    p = db.query(ActionProposal).filter(ActionProposal.id == proposal_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    if p.status not in ("PENDING", "CONTESTED"):
        raise HTTPException(status_code=409, detail=f"Proposal is already '{p.status}'.")

    p.status = "CONFIRMED"
    p.reviewed_by = current_user.id
    p.reviewed_at = app_now()
    p.review_note = payload.note

    # Execute the proposed action
    _execute_proposal(db, p, current_user)

    audit_service.write_audit(
        db,
        entity_type="proposal",
        entity_id=p.id,
        action="PROPOSAL_CONFIRMED",
        payload={"proposal_type": p.proposal_type, "reviewer_id": current_user.id, "note": payload.note},
        actor_id=current_user.id,
        actor_role=current_user.role,
        rationale=f"Manager confirmed proposal #{p.id}: {p.proposal_type}",
    )
    db.commit()
    db.refresh(p)
    return p


@router.post("/{proposal_id}/reject", response_model=ProposalOut)
def reject_proposal(
    proposal_id: int,
    payload: ProposalReviewAction = ProposalReviewAction(),
    db: Session = Depends(get_db),
    current_user=Depends(get_manager_or_admin),
):
    p = db.query(ActionProposal).filter(ActionProposal.id == proposal_id).first()
    if not p:
        raise HTTPException(status_code=404, detail="Proposal not found.")
    if p.status not in ("PENDING", "CONTESTED"):
        raise HTTPException(status_code=409, detail=f"Proposal is already '{p.status}'.")

    p.status = "REJECTED"
    p.reviewed_by = current_user.id
    p.reviewed_at = app_now()
    p.review_note = payload.note

    # If it was a NO_SHOW_PENALTY booking, revert it to APPROVED so user can still check in
    if p.proposal_type == "NO_SHOW_PENALTY" and p.entity_type == "booking":
        booking = db.query(Booking).filter(Booking.id == p.entity_id).first()
        if booking and booking.status == "NO_SHOW_PROPOSED":
            booking.status = "APPROVED"

    audit_service.write_audit(
        db,
        entity_type="proposal",
        entity_id=p.id,
        action="PROPOSAL_REJECTED",
        payload={"proposal_type": p.proposal_type, "reviewer_id": current_user.id, "note": payload.note},
        actor_id=current_user.id,
        actor_role=current_user.role,
        rationale=f"Manager dismissed proposal #{p.id}: {p.proposal_type}. Note: {payload.note}",
    )
    db.commit()
    db.refresh(p)
    return p


def _execute_proposal(db: Session, proposal: ActionProposal, reviewer: User) -> None:
    """Apply the proposed_payload side effects."""
    pp = proposal.proposed_payload

    if proposal.proposal_type == "NO_SHOW_PENALTY":
        booking = db.query(Booking).filter(Booking.id == pp["booking_id"]).first()
        if not booking:
            return
        booking.status = "NO_SHOW"
        user = db.query(User).filter(User.id == pp["user_id"]).first()
        if user:
            credit_service.forfeit_credits(
                db, user, pp["credits_to_forfeit"], booking.id,
                actor_id=reviewer.id, actor_role=reviewer.role,
            )
            # Issue a NO_SHOW strike
            strike = Strike(
                user_id=user.id,
                issued_by=reviewer.id,
                strike_type="NO_SHOW",
                reason=f"No-show for booking #{booking.id}.",
                booking_id=booking.id,
                proposal_id=proposal.id,
            )
            db.add(strike)
            db.flush()
            user.strike_count += 1
            notification_service.notify(
                db, user.id,
                title="Strike Issued — No Show",
                message=f"A NO_SHOW strike has been recorded for booking #{booking.id}.",
                notif_type="STRIKE",
                entity_type="booking",
                entity_id=booking.id,
            )
            audit_service.write_audit(
                db,
                entity_type="booking",
                entity_id=booking.id,
                action="BOOKING_NO_SHOW",
                payload={"credits_forfeited": pp["credits_to_forfeit"], "strike_id": strike.id},
                actor_id=reviewer.id,
                actor_role=reviewer.role,
                rationale=f"Manager confirmed no-show proposal #{proposal.id}.",
            )

    elif proposal.proposal_type == "STRIKE_PROPOSAL":
        user = db.query(User).filter(User.id == pp.get("user_id")).first()
        if user:
            strike = Strike(
                user_id=user.id,
                issued_by=reviewer.id,
                strike_type=pp.get("strike_type", "MISSED_SESSION_NO_SIGNAL"),
                reason=pp.get("reason", "Missed session with no check-in or signal."),
                booking_id=pp.get("booking_id"),
                proposal_id=proposal.id,
            )
            db.add(strike)
            db.flush()
            user.strike_count += 1
            notification_service.notify(
                db,
                user.id,
                title="Strike Confirmed ⚠️",
                message=f"A strike has been confirmed by lab manager {reviewer.full_name}: {strike.reason}",
                notif_type="STRIKE",
                entity_type="strike",
                entity_id=strike.id,
            )
            audit_service.write_audit(
                db,
                entity_type="strike",
                entity_id=strike.id,
                action="STRIKE_CONFIRMED",
                payload={"user_id": user.id, "strike_type": strike.strike_type, "reviewer_id": reviewer.id},
                actor_id=reviewer.id,
                actor_role=reviewer.role,
                rationale=f"Manager confirmed strike proposal #{proposal.id}.",
            )

    elif proposal.proposal_type == "LATE_RETURN_PENALTY":
        user = db.query(User).filter(User.id == pp.get("user_id")).first()
        fee = pp.get("proposed_penalty_credits", 0)
        b_id = pp.get("booking_id")
        if user and fee > 0:
            credit_service.deduct_credits(db, user, fee, b_id, reviewer.id)
            notification_service.notify(
                db,
                user.id,
                title="Late Fee Confirmed",
                message=f"An overtime deduction of {fee} credits was confirmed by manager {reviewer.full_name} for overdue return of booking #{b_id}.",
                notif_type="CREDIT_UPDATE",
                entity_type="booking",
                entity_id=b_id,
            )
            audit_service.write_audit(
                db,
                entity_type="booking",
                entity_id=b_id,
                action="LATE_PENALTY_CONFIRMED",
                payload={"overtime_fee": fee, "reviewer_id": reviewer.id},
                actor_id=reviewer.id,
                actor_role=reviewer.role,
                rationale=f"Manager confirmed late fee proposal #{proposal.id}: {fee} credits.",
            )
