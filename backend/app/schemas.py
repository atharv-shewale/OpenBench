"""
Pydantic schemas (request / response) for OpenBench.
All in one file for hackathon speed; split into modules as needed.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, EmailStr, field_validator, model_validator


# ─────────────────────────────────────────────────────────────────────────────
# Auth
# ─────────────────────────────────────────────────────────────────────────────

class UserRegister(BaseModel):
    email: EmailStr
    full_name: str
    password: str
    organisation: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


# ─────────────────────────────────────────────────────────────────────────────
# Users
# ─────────────────────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: str
    credit_balance: int
    credit_held: int
    organisation: Optional[str]
    is_active: bool
    strike_count: int
    created_at: datetime

    model_config = {"from_attributes": True}


class UserUpdateAdmin(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    organisation: Optional[str] = None


class LabMembershipCreate(BaseModel):
    lab_id: int
    role: str  # owner | manager


# ─────────────────────────────────────────────────────────────────────────────
# Labs
# ─────────────────────────────────────────────────────────────────────────────

class LabCreate(BaseModel):
    name: str
    institution: str
    city: str
    description: Optional[str] = None
    contact_email: Optional[str] = None


class LabOut(BaseModel):
    id: int
    name: str
    institution: str
    city: str
    description: Optional[str]
    contact_email: Optional[str]
    is_active: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class LabOutWithCount(LabOut):
    equipment_count: int = 0


# ─────────────────────────────────────────────────────────────────────────────
# Equipment
# ─────────────────────────────────────────────────────────────────────────────

class AvailabilityWindowIn(BaseModel):
    day_of_week: int   # 0-6
    start_time: str    # "HH:MM"
    end_time: str


class AvailabilityWindowOut(AvailabilityWindowIn):
    id: int
    model_config = {"from_attributes": True}


class EquipmentCreate(BaseModel):
    lab_id: int
    name: str
    type: str
    description: Optional[str] = None
    credit_per_hour: int
    max_booking_hours: int = 4
    image_url: Optional[str] = None
    rules: Optional[Dict[str, Any]] = None
    required_credentials: Optional[List[str]] = None
    availability_windows: List[AvailabilityWindowIn] = []


class EquipmentUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    credit_per_hour: Optional[int] = None
    max_booking_hours: Optional[int] = None
    status: Optional[str] = None
    rules: Optional[Dict[str, Any]] = None
    required_credentials: Optional[List[str]] = None
    availability_windows: Optional[List[AvailabilityWindowIn]] = None


class EquipmentOut(BaseModel):
    id: int
    lab_id: int
    lab_name: Optional[str] = None
    name: str
    type: str
    description: Optional[str]
    credit_per_hour: int
    max_booking_hours: int
    status: str
    image_url: Optional[str]
    rules: Optional[Dict[str, Any]]
    required_credentials: Optional[List[str]]
    availability_windows: List[AvailabilityWindowOut] = []
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Bookings
# ─────────────────────────────────────────────────────────────────────────────

class BookingCreate(BaseModel):
    equipment_id: int
    slot_start: datetime
    slot_end: datetime
    purpose: Optional[str] = None


class BookingManagerAction(BaseModel):
    note: Optional[str] = None
    decision_reason: Optional[Dict[str, Any]] = None


class BookingOut(BaseModel):
    id: int
    user_id: int
    equipment_id: int
    status: str
    slot_start: datetime
    slot_end: datetime
    checked_in_at: Optional[datetime]
    checked_out_at: Optional[datetime]
    credits_held: int
    credits_charged: int
    purpose: Optional[str]
    manager_note: Optional[str]
    decision_reason: Optional[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class CheckoutResponse(BaseModel):
    booking: BookingOut
    credit_balance_after: int


# ─────────────────────────────────────────────────────────────────────────────
# Waitlist
# ─────────────────────────────────────────────────────────────────────────────

class WaitlistCreate(BaseModel):
    equipment_id: int
    desired_start: datetime
    desired_end: datetime


class WaitlistOut(BaseModel):
    id: int
    user_id: int
    equipment_id: int
    desired_start: datetime
    desired_end: datetime
    status: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Condition Reports
# ─────────────────────────────────────────────────────────────────────────────

class ConditionReportCreate(BaseModel):
    booking_id: int
    report_type: str      # PRE | POST
    condition: str        # GOOD | FAIR | DAMAGED | BROKEN
    notes: Optional[str] = None
    photos_json: Optional[List[str]] = None


class ConditionReportOut(ConditionReportCreate):
    id: int
    reporter_id: int
    created_at: datetime
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Incidents
# ─────────────────────────────────────────────────────────────────────────────

class IncidentCreate(BaseModel):
    booking_id: int
    severity: str       # LOW | MEDIUM | HIGH | CRITICAL
    description: str


class IncidentOut(BaseModel):
    id: int
    booking_id: int
    reported_by: int
    severity: str
    description: str
    resolution: Optional[str]
    resolved_at: Optional[datetime]
    status: str
    created_at: datetime
    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Proposals
# ─────────────────────────────────────────────────────────────────────────────

class ProposalReviewAction(BaseModel):
    note: Optional[str] = None


class ProposalOut(BaseModel):
    id: int
    proposal_type: str
    entity_type: str
    entity_id: int
    triggered_by: str
    rationale: str
    proposed_payload: Dict[str, Any]
    status: str
    reviewed_by: Optional[int]
    reviewed_at: Optional[datetime]
    review_note: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# Credits
# ─────────────────────────────────────────────────────────────────────────────

class CreditBalance(BaseModel):
    user_id: int
    credit_balance: int
    credit_held: int
    spendable: int


class CreditTransactionOut(BaseModel):
    id: int
    user_id: int
    booking_id: Optional[int]
    tx_type: str
    amount: int
    balance_after: int
    description: Optional[str]
    created_at: datetime
    model_config = {"from_attributes": True}


class AdminCreditGrant(BaseModel):
    user_id: int
    amount: int
    description: Optional[str] = None


# ─────────────────────────────────────────────────────────────────────────────
# Audit Log
# ─────────────────────────────────────────────────────────────────────────────

class AuditLogOut(BaseModel):
    id: int
    entity_type: str
    entity_id: int
    action: str
    actor_id: Optional[int]
    actor_role: Optional[str]
    payload: Dict[str, Any]
    rationale: Optional[str]
    prev_hash: str
    hash: str
    created_at: datetime
    model_config = {"from_attributes": True}


class AuditPage(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[AuditLogOut]


class ChainVerifyResult(BaseModel):
    chain_valid: bool
    total_entries: int
    first_entry_id: Optional[int] = None
    last_entry_id: Optional[int] = None
    broken_at_id: Optional[int] = None


# ─────────────────────────────────────────────────────────────────────────────
# Admin / Clock
# ─────────────────────────────────────────────────────────────────────────────

class ClockState(BaseModel):
    real_utc: datetime
    app_now: datetime
    offset_seconds: int


class ClockAdvance(BaseModel):
    seconds: int


class NotificationOut(BaseModel):
    id: int
    user_id: int
    title: str
    message: str
    notif_type: str
    entity_type: Optional[str]
    entity_id: Optional[int]
    is_read: bool
    created_at: datetime
    model_config = {"from_attributes": True}


class UserCredentialCreate(BaseModel):
    credential_type: str
    issued_by: Optional[str] = None
    issued_at: datetime
    expires_at: Optional[datetime] = None
    document_url: Optional[str] = None
    notes: Optional[str] = None


class UserCredentialOut(UserCredentialCreate):
    id: int
    user_id: int
    is_verified: bool
    verified_by: Optional[int]
    created_at: datetime
    model_config = {"from_attributes": True}

