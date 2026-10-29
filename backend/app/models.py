"""
SQLAlchemy ORM models for OpenBench.

All models live in this single file for hackathon clarity.
Every timestamp column defaults to app_now() — never datetime.utcnow().
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.clock import app_now
from app.database import Base


# ─────────────────────────────────────────────────────────────────────────────
# USERS
# ─────────────────────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False, default="user")
    # credit_balance = spendable credits; credit_held = reserved for pending/approved bookings
    credit_balance: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    credit_held: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    organisation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Running count of confirmed strikes; cached for fast queries
    strike_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=app_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=app_now, onupdate=app_now)

    # relationships
    bookings: Mapped[List["Booking"]] = relationship(
        "Booking", back_populates="user", foreign_keys="Booking.user_id"
    )
    credentials: Mapped[List["UserCredential"]] = relationship(
        "UserCredential", back_populates="user", foreign_keys="UserCredential.user_id"
    )
    credit_transactions: Mapped[List["CreditTransaction"]] = relationship(
        "CreditTransaction", back_populates="user"
    )
    notifications: Mapped[List["Notification"]] = relationship(
        "Notification", back_populates="user"
    )
    strikes: Mapped[List["Strike"]] = relationship(
        "Strike", back_populates="user", foreign_keys="Strike.user_id"
    )
    lab_memberships: Mapped[List["LabMembership"]] = relationship(
        "LabMembership", back_populates="user"
    )
    badges: Mapped[List["Badge"]] = relationship(
        "Badge", back_populates="user", foreign_keys="Badge.user_id"
    )


class UserCredential(Base):
    """
    Certifications / qualifications a user holds.
    Certain equipment requires specific credentials (e.g. LASER_SAFETY_L1).
    Credentials can expire.
    """
    __tablename__ = "user_credentials"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    credential_type: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. LASER_SAFETY_L1
    issued_by: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    issued_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    expires_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)  # None = no expiry
    is_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verified_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    document_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=app_now)

    user: Mapped["User"] = relationship("User", back_populates="credentials", foreign_keys=[user_id])
    verifier: Mapped[Optional["User"]] = relationship("User", foreign_keys=[verified_by])


# ─────────────────────────────────────────────────────────────────────────────
# LABS & EQUIPMENT
# ─────────────────────────────────────────────────────────────────────────────

class Lab(Base):
    __tablename__ = "labs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    institution: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=app_now)

    equipment: Mapped[List["Equipment"]] = relationship("Equipment", back_populates="lab")
    memberships: Mapped[List["LabMembership"]] = relationship("LabMembership", back_populates="lab")


class LabMembership(Base):
    __tablename__ = "lab_memberships"
    __table_args__ = (UniqueConstraint("user_id", "lab_id", name="uq_lab_membership"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    lab_id: Mapped[int] = mapped_column(Integer, ForeignKey("labs.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # owner | manager
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=app_now)

    user: Mapped["User"] = relationship("User", back_populates="lab_memberships")
    lab: Mapped["Lab"] = relationship("Lab", back_populates="memberships")


class Equipment(Base):
    """
    A bookable resource (machine, instrument, or space) within a lab.
    `rules` is a JSON dict of freeform usage rules shown to users at booking time.
    `required_credentials` is a JSON list of credential_type strings.
    """
    __tablename__ = "equipment"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    lab_id: Mapped[int] = mapped_column(Integer, ForeignKey("labs.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[str] = mapped_column(String(50), nullable=False)          # fabrication|testing|space|other
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    credit_per_hour: Mapped[int] = mapped_column(Integer, nullable=False)
    max_booking_hours: Mapped[int] = mapped_column(Integer, nullable=False, default=4)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="available")  # available|maintenance|retired
    image_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    photos: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(255), nullable=True) # Specific room, bench or wing
    access_conditions: Mapped[Optional[str]] = mapped_column(Text, nullable=True) # e.g. Accompanied by staff, safety gear
    deposit_credits: Mapped[int] = mapped_column(Integer, nullable=False, default=0) # Security deposit in credits
    approver_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    rules: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    required_credentials: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=app_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=app_now, onupdate=app_now)

    lab: Mapped["Lab"] = relationship("Lab", back_populates="equipment")
    approver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[approver_id])
    bookings: Mapped[List["Booking"]] = relationship("Booking", back_populates="equipment")
    availability_windows: Mapped[List["EquipmentAvailabilityWindow"]] = relationship(
        "EquipmentAvailabilityWindow", back_populates="equipment", cascade="all, delete-orphan"
    )


class EquipmentAvailabilityWindow(Base):
    """Recurring weekly window during which a resource can be booked."""
    __tablename__ = "equipment_availability_windows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    equipment_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("equipment.id", ondelete="CASCADE"), nullable=False
    )
    day_of_week: Mapped[int] = mapped_column(Integer, nullable=False)  # 0=Mon … 6=Sun
    start_time: Mapped[str] = mapped_column(String(5), nullable=False)  # "HH:MM"
    end_time: Mapped[str] = mapped_column(String(5), nullable=False)

    equipment: Mapped["Equipment"] = relationship("Equipment", back_populates="availability_windows")


# ─────────────────────────────────────────────────────────────────────────────
# BOOKINGS & RELATED
# ─────────────────────────────────────────────────────────────────────────────

class Booking(Base):
    """
    Core booking record. See CONTEXT.md §7 for the full state machine.
    `decision_reason` is a JSON dict written when a manager approves/rejects:
        { "criterion": "...", "notes": "...", "automated": false }
    """
    __tablename__ = "bookings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    equipment_id: Mapped[int] = mapped_column(Integer, ForeignKey("equipment.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(25), nullable=False, default="PENDING", index=True)
    slot_start: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    slot_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    checked_in_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    checked_out_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    credits_held: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    credits_charged: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    priority_tier: Mapped[str] = mapped_column(String(20), nullable=False, default="STANDARD")  # STANDARD | PRIORITY | RESEARCH | EMERGENCY
    group_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)  # Student team, startup group, MSME department
    has_supervisor_signoff: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    supervisor_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    purpose: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    manager_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    decision_reason: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=app_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=app_now, onupdate=app_now)

    user: Mapped["User"] = relationship("User", back_populates="bookings", foreign_keys=[user_id])
    equipment: Mapped["Equipment"] = relationship("Equipment", back_populates="bookings")
    condition_reports: Mapped[List["ConditionReport"]] = relationship(
        "ConditionReport", back_populates="booking"
    )
    incidents: Mapped[List["Incident"]] = relationship("Incident", back_populates="booking")
    waitlist_entries: Mapped[List["WaitlistEntry"]] = relationship(
        "WaitlistEntry", back_populates="original_booking"
    )


class WaitlistEntry(Base):
    """
    Users can join the waitlist for a slot that is already fully booked.
    When the blocking booking is cancelled/rejected, waitlisted users are notified.
    """
    __tablename__ = "waitlist"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    equipment_id: Mapped[int] = mapped_column(Integer, ForeignKey("equipment.id"), nullable=False)
    original_booking_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True
    )
    desired_start: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    desired_end: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    # WAITING | NOTIFIED | EXPIRED | CONVERTED
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="WAITING")
    notified_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=app_now)

    user: Mapped["User"] = relationship("User")
    equipment: Mapped["Equipment"] = relationship("Equipment")
    original_booking: Mapped[Optional["Booking"]] = relationship(
        "Booking", back_populates="waitlist_entries"
    )


class ConditionReport(Base):
    """
    Pre/post session condition report filed by user or manager.
    Tracks equipment health over time and establishes liability.
    """
    __tablename__ = "condition_reports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(Integer, ForeignKey("bookings.id"), nullable=False)
    reporter_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    report_type: Mapped[str] = mapped_column(String(20), nullable=False)   # PRE | POST
    condition: Mapped[str] = mapped_column(String(20), nullable=False)      # GOOD | FAIR | DAMAGED | BROKEN
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    photos_json: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=app_now)

    booking: Mapped["Booking"] = relationship("Booking", back_populates="condition_reports")
    reporter: Mapped["User"] = relationship("User", foreign_keys=[reporter_id])


class Incident(Base):
    """
    Safety or equipment incident raised during or after a session.
    Severity drives escalation; resolution requires manager action.
    """
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    booking_id: Mapped[int] = mapped_column(Integer, ForeignKey("bookings.id"), nullable=False)
    reported_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    severity: Mapped[str] = mapped_column(String(20), nullable=False)      # LOW | MEDIUM | HIGH | CRITICAL
    description: Mapped[str] = mapped_column(Text, nullable=False)
    resolution: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    resolved_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="OPEN")  # OPEN|INVESTIGATING|RESOLVED
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=app_now)

    booking: Mapped["Booking"] = relationship("Booking", back_populates="incidents")
    reporter: Mapped["User"] = relationship("User", foreign_keys=[reported_by])
    resolver: Mapped[Optional["User"]] = relationship("User", foreign_keys=[resolved_by])


# ─────────────────────────────────────────────────────────────────────────────
# STRIKES
# ─────────────────────────────────────────────────────────────────────────────

class Strike(Base):
    """
    A formal penalty issued to a user by a manager.
    Strikes are always created via an ActionProposal (human-in-the-loop).
    3 strikes → automatic account suspension proposal.
    """
    __tablename__ = "strikes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    issued_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    strike_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # NO_SHOW | DAMAGE | MISCONDUCT | POLICY_VIOLATION
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    booking_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True
    )
    proposal_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("action_proposals.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=app_now)

    user: Mapped["User"] = relationship("User", back_populates="strikes", foreign_keys=[user_id])
    issuer: Mapped["User"] = relationship("User", foreign_keys=[issued_by])


# ─────────────────────────────────────────────────────────────────────────────
# CREDITS
# ─────────────────────────────────────────────────────────────────────────────

class CreditTransaction(Base):
    """
    Immutable credit ledger. Never updated or deleted.
    `amount` is positive for credits in, negative for credits out.
    `balance_after` is a snapshot of credit_balance after this transaction.
    """
    __tablename__ = "credit_transactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    booking_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("bookings.id", ondelete="SET NULL"), nullable=True
    )
    tx_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # WELCOME_GRANT | HOLD | HOLD_RELEASE | DEDUCT | FORFEIT | ADMIN_GRANT | ADMIN_DEDUCT
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    balance_after: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=app_now)

    user: Mapped["User"] = relationship("User", back_populates="credit_transactions")


# ─────────────────────────────────────────────────────────────────────────────
# PROPOSALS (human-in-the-loop)
# ─────────────────────────────────────────────────────────────────────────────

class ActionProposal(Base):
    """
    An automated action proposed by APScheduler or AI that requires
    a manager/admin to confirm before it takes effect.

    `rationale` must explain in plain English *why* this action is proposed.
    `proposed_payload` is the exact JSON that will be applied on confirm.
    """
    __tablename__ = "action_proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    proposal_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    # NO_SHOW_PENALTY | AUTO_CANCEL | BADGE_AWARD | STRIKE_ISSUE | SUSPEND_USER
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False)
    triggered_by: Mapped[str] = mapped_column(String(50), nullable=False)  # scheduler | ai | system
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PENDING", index=True)
    # PENDING | CONFIRMED | REJECTED
    reviewed_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    review_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=app_now)

    reviewer: Mapped[Optional["User"]] = relationship("User", foreign_keys=[reviewed_by])


# ─────────────────────────────────────────────────────────────────────────────
# NOTIFICATIONS
# ─────────────────────────────────────────────────────────────────────────────

class Notification(Base):
    """In-app notification delivered to a user."""
    __tablename__ = "notifications"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    notif_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # BOOKING_UPDATE | CREDIT_UPDATE | WAITLIST | STRIKE | SYSTEM
    entity_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_read: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=app_now)

    user: Mapped["User"] = relationship("User", back_populates="notifications")


# ─────────────────────────────────────────────────────────────────────────────
# BADGES
# ─────────────────────────────────────────────────────────────────────────────

class Badge(Base):
    __tablename__ = "badges"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    badge_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # FIRST_BOOKING | POWER_USER | NO_SHOW_FREE | RELIABLE_RETURNER | etc.
    awarded_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=app_now)
    awarded_by: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    proposal_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("action_proposals.id", ondelete="SET NULL"), nullable=True
    )

    user: Mapped["User"] = relationship("User", back_populates="badges", foreign_keys=[user_id])
    awarder: Mapped[Optional["User"]] = relationship("User", foreign_keys=[awarded_by])


# ─────────────────────────────────────────────────────────────────────────────
# AUDIT LOG (append-only, hash-chained)
# ─────────────────────────────────────────────────────────────────────────────

class AuditLog(Base):
    """
    Immutable, hash-chained audit log.
    - Never UPDATE or DELETE rows in this table.
    - Every row's `hash` covers its own content + `prev_hash` of the previous row.
    - Genesis row (id=1) has prev_hash = "0" * 64.
    - See app/services/audit_service.py for write and verify functions.
    """
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    entity_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    action: Mapped[str] = mapped_column(String(80), nullable=False, index=True)
    actor_id: Mapped[Optional[int]] = mapped_column(Integer, nullable=True, index=True)
    actor_role: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    rationale: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prev_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    # Always set to app_now() — never datetime.utcnow()
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

