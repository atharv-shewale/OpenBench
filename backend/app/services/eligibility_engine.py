"""
Pure eligibility engine for OpenBench.

All functions are pure, deterministic, and take explicit inputs (data dicts/dataclasses/primitives),
making them 100% unit-testable without database mocks or network calls.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional, Set


@dataclass(frozen=True)
class RuleResult:
    rule_name: str
    passed: bool
    reason: str
    category: str  # "credentials", "standing", "credits", "schedule", "supervision"


@dataclass
class EligibilityEvaluation:
    is_eligible: bool
    results: List[RuleResult] = field(default_factory=list)
    reasons_failed: List[str] = field(default_factory=list)

    def add(self, result: RuleResult) -> None:
        self.results.append(result)
        if not result.passed:
            self.is_eligible = False
            self.reasons_failed.append(result.reason)


# ── Rule 1: Credentials & Expiry ───────────────────────────────────────────────

def check_credentials_rule(
    required_credentials: List[str],
    user_credentials: List[Dict[str, Any]],
    current_time: datetime,
) -> RuleResult:
    """
    Validates that user possesses every required certification:
    - Must be marked is_verified=True
    - expires_at must be None or > current_time
    """
    if not required_credentials:
        return RuleResult(
            rule_name="Required Credentials",
            passed=True,
            reason="No specialized certifications required for this resource.",
            category="credentials",
        )

    # Filter active verified credentials
    valid_held: Set[str] = set()
    expired_held: Set[str] = set()
    unverified_held: Set[str] = set()

    for cred in user_credentials:
        ctype = cred.get("credential_type")
        is_verified = cred.get("is_verified", False)
        expires_at = cred.get("expires_at")

        if not is_verified:
            unverified_held.add(ctype)
            continue

        if expires_at is not None and expires_at <= current_time:
            expired_held.add(ctype)
            continue

        valid_held.add(ctype)

    missing = [c for c in required_credentials if c not in valid_held]

    if not missing:
        return RuleResult(
            rule_name="Required Credentials",
            passed=True,
            reason=f"All {len(required_credentials)} required certification(s) verified and active.",
            category="credentials",
        )

    # Build human-friendly explanation
    details = []
    for c in missing:
        if c in expired_held:
            details.append(f"{c} (expired)")
        elif c in unverified_held:
            details.append(f"{c} (pending verification)")
        else:
            details.append(f"{c} (missing)")

    return RuleResult(
        rule_name="Required Credentials",
        passed=False,
        reason=f"Missing active certifications: {', '.join(details)}.",
        category="credentials",
    )


# ── Rule 2: Account Standing, Role & Strikes ──────────────────────────────────

def check_account_standing_rule(
    is_active: bool,
    strike_count: int,
    user_role: str,
    allowed_roles: Optional[List[str]] = None,
) -> RuleResult:
    """
    Validates:
    - User account is active
    - Strike count < 3
    - User role matches allowed roles if specified by equipment rule
    """
    if not is_active:
        return RuleResult(
            rule_name="Account Standing",
            passed=False,
            reason="Your user account has been deactivated.",
            category="standing",
        )

    if strike_count >= 3:
        return RuleResult(
            rule_name="Disciplinary Standing",
            passed=False,
            reason=f"Account is suspended with {strike_count} strikes (threshold is 3).",
            category="standing",
        )

    if allowed_roles and user_role not in allowed_roles:
        return RuleResult(
            rule_name="Role & Membership",
            passed=False,
            reason=f"This equipment requires one of these roles: {', '.join(allowed_roles)}. You are '{user_role}'.",
            category="standing",
        )

    return RuleResult(
        rule_name="Account Standing",
        passed=True,
        reason=f"Account active in good standing ({strike_count}/3 strikes).",
        category="standing",
    )


# ── Rule 3: Supervisor Sign-Off ───────────────────────────────────────────────

def check_supervisor_signoff_rule(
    requires_supervisor: bool,
    has_supervisor_signoff: bool,
    supervisor_name: Optional[str] = None,
) -> RuleResult:
    """
    Some high-risk equipment (e.g. wet chemistry, heavy CNC, high voltage)
    requires a faculty or lab manager sign-off prior to booking approval.
    """
    if not requires_supervisor:
        return RuleResult(
            rule_name="Supervisor Sign-off",
            passed=True,
            reason="Independent operation permitted; no supervisor sign-off required.",
            category="supervision",
        )

    if has_supervisor_signoff:
        return RuleResult(
            rule_name="Supervisor Sign-off",
            passed=True,
            reason=f"Supervisor endorsement on file{' (' + supervisor_name + ')' if supervisor_name else ''}.",
            category="supervision",
        )

    return RuleResult(
        rule_name="Supervisor Sign-off",
        passed=False,
        reason="Operation requires verified supervisor endorsement before booking can proceed.",
        category="supervision",
    )


# ── Rule 4: Credits & Deposit ─────────────────────────────────────────────────

def check_credits_and_deposit_rule(
    spendable_credits: int,
    duration_hours: float,
    credit_per_hour: int,
    deposit_credits: int = 0,
) -> RuleResult:
    """
    Validates that user has spendable credits >= (duration_hours * rate) + deposit.
    """
    cost = int(duration_hours * credit_per_hour)
    required = cost + deposit_credits

    if spendable_credits >= required:
        return RuleResult(
            rule_name="Credits & Deposit",
            passed=True,
            reason=f"Spendable balance ({spendable_credits} cr) covers {cost} cr usage + {deposit_credits} cr deposit.",
            category="credits",
        )

    shortfall = required - spendable_credits
    return RuleResult(
        rule_name="Credits & Deposit",
        passed=False,
        reason=f"Insufficient spendable credits. Need {required} cr ({cost} usage + {deposit_credits} deposit), but you have {spendable_credits} cr (short by {shortfall} cr).",
        category="credits",
    )


# ── Rule 5: Schedule & Availability Windows ───────────────────────────────────

def check_slot_window_rule(
    slot_start: datetime,
    slot_end: datetime,
    max_booking_hours: int,
    availability_windows: List[Dict[str, Any]],
) -> RuleResult:
    """
    Validates:
    - slot_end > slot_start
    - duration <= max_booking_hours
    - Slot falls within at least one operating window for its day of week
    """
    duration_hours = (slot_end - slot_start).total_seconds() / 3600.0

    if duration_hours <= 0:
        return RuleResult(
            rule_name="Slot Schedule",
            passed=False,
            reason="Slot end time must be after slot start time.",
            category="schedule",
        )

    if duration_hours > max_booking_hours:
        return RuleResult(
            rule_name="Slot Duration",
            passed=False,
            reason=f"Requested duration ({duration_hours:.1f}h) exceeds maximum allowed ({max_booking_hours}h).",
            category="schedule",
        )

    if not availability_windows:
        # If no explicit windows are configured, lab is available 24/7 or standard hours
        return RuleResult(
            rule_name="Operating Windows",
            passed=True,
            reason="Slot is within open schedule.",
            category="schedule",
        )

    slot_day = slot_start.weekday()  # 0=Monday, 6=Sunday
    req_start_time = slot_start.time()
    req_end_time = slot_end.time()

    day_windows = [w for w in availability_windows if w.get("day_of_week") == slot_day]

    if not day_windows:
        day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        return RuleResult(
            rule_name="Operating Windows",
            passed=False,
            reason=f"Equipment is closed on {day_names[slot_day]}s.",
            category="schedule",
        )

    within_window = False
    for w in day_windows:
        try:
            w_start_str = w.get("start_time", "00:00")
            w_end_str = w.get("end_time", "23:59")
            sh, sm = map(int, w_start_str.split(":")[:2])
            eh, em = map(int, w_end_str.split(":")[:2])
            w_start = time(sh, sm)
            w_end = time(eh, em)

            if req_start_time >= w_start and req_end_time <= w_end and slot_start.date() == slot_end.date():
                within_window = True
                break
        except Exception:
            continue

    if within_window:
        return RuleResult(
            rule_name="Operating Windows",
            passed=True,
            reason="Requested slot falls within scheduled lab operating hours.",
            category="schedule",
        )

    return RuleResult(
        rule_name="Operating Windows",
        passed=False,
        reason=f"Requested time ({slot_start.strftime('%H:%M')}–{slot_end.strftime('%H:%M')}) is outside operating hours.",
        category="schedule",
    )


# ── Aggregate Evaluation ──────────────────────────────────────────────────────

def evaluate_booking_eligibility(
    user_data: Dict[str, Any],
    equipment_data: Dict[str, Any],
    booking_request: Dict[str, Any],
    current_time: datetime,
) -> EligibilityEvaluation:
    """
    Evaluates all rules in sequence and produces an EligibilityEvaluation.
    """
    evaluation = EligibilityEvaluation(is_eligible=True)

    # 1. Credentials
    required_credentials = equipment_data.get("required_credentials") or []
    user_credentials = user_data.get("credentials") or []
    evaluation.add(check_credentials_rule(required_credentials, user_credentials, current_time))

    # 2. Account standing & Role
    allowed_roles = (equipment_data.get("rules") or {}).get("allowed_roles")
    evaluation.add(check_account_standing_rule(
        is_active=user_data.get("is_active", True),
        strike_count=user_data.get("strike_count", 0),
        user_role=user_data.get("role", "user"),
        allowed_roles=allowed_roles,
    ))

    # 3. Supervisor sign-off
    requires_supervisor = (equipment_data.get("rules") or {}).get("requires_supervisor", False)
    evaluation.add(check_supervisor_signoff_rule(
        requires_supervisor=requires_supervisor,
        has_supervisor_signoff=booking_request.get("has_supervisor_signoff", False),
        supervisor_name=booking_request.get("supervisor_name"),
    ))

    # 4. Schedule & Window
    slot_start = booking_request["slot_start"]
    slot_end = booking_request["slot_end"]
    max_booking_hours = equipment_data.get("max_booking_hours", 4)
    availability_windows = equipment_data.get("availability_windows") or []
    evaluation.add(check_slot_window_rule(
        slot_start=slot_start,
        slot_end=slot_end,
        max_booking_hours=max_booking_hours,
        availability_windows=availability_windows,
    ))

    # 5. Credits
    duration_hours = max(0.0, (slot_end - slot_start).total_seconds() / 3600.0)
    evaluation.add(check_credits_and_deposit_rule(
        spendable_credits=user_data.get("spendable_credits", 0),
        duration_hours=duration_hours,
        credit_per_hour=equipment_data.get("credit_per_hour", 10),
        deposit_credits=equipment_data.get("deposit_credits", 0),
    ))

    return evaluation
