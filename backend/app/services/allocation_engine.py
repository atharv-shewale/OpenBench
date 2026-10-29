"""
Allocation Engine for OpenBench.

Implements allocation constraints and deterministic waitlist ranking:
1. Rolling weekly hour cap per user and per group
2. Max active concurrent bookings limit
3. Max advance booking window
4. Prime-slot detection and cooldown rules
5. Waitlist ranking score = purpose priority + first-time-user boost + inverse recent usage
   + waiting-time bonus - no-show penalty (weights in config)
6. Complete score breakdown calculation for "Why this outcome?" explanation.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, time, timedelta
from typing import Any, Dict, List, Optional


# ── Configuration & Weights ───────────────────────────────────────────────────

ALLOCATION_CONFIG = {
    "MAX_WEEKLY_HOURS_PER_USER": 12.0,       # Max booking hours in a rolling 7-day window
    "MAX_WEEKLY_HOURS_PER_GROUP": 24.0,      # Max booking hours across an entire group/team
    "MAX_ACTIVE_BOOKINGS_PER_USER": 3,       # Max PENDING or APPROVED or IN_PROGRESS bookings
    "MAX_ADVANCE_BOOKING_DAYS": 14,          # How far in advance a slot can be booked
    "PRIME_START_HOUR": 13,                  # Prime time: 13:00 (1 PM)
    "PRIME_END_HOUR": 17,                    # Prime time: 17:00 (5 PM)
    "PRIME_COOLDOWN_HOURS": 48.0,            # Hours required between booking prime slots on same machine

    # Waitlist Scoring Weights
    "PURPOSE_PRIORITY_WEIGHTS": {
        "EMERGENCY": 40.0,
        "RESEARCH": 25.0,
        "PRIORITY": 15.0,
        "STANDARD": 5.0,
    },
    "FIRST_TIME_USER_BOOST": 20.0,           # Boost for users with 0 prior completed bookings
    "INVERSE_RECENT_USAGE_WEIGHT": 2.0,       # Points given for unused hours under weekly cap
    "WAITING_TIME_HOURLY_BONUS": 1.5,        # Points per hour spent in waitlist
    "MAX_WAITING_BONUS": 30.0,
    "NO_SHOW_PENALTY_PER_STRIKE": 15.0,      # Deduction per strike on user record
}


@dataclass(frozen=True)
class AllocationCheckResult:
    allowed: bool
    reason: str
    rule_name: str
    details: Dict[str, Any] = field(default_factory=dict)


# ── Allocation Constraint Checks ──────────────────────────────────────────────

def is_prime_slot(
    slot_start: datetime,
    slot_end: datetime,
    config: Dict[str, Any] = ALLOCATION_CONFIG,
) -> bool:
    """Checks if any portion of the slot intersects prime hours (e.g. 13:00 - 17:00)."""
    p_start = time(config.get("PRIME_START_HOUR", 13), 0)
    p_end = time(config.get("PRIME_END_HOUR", 17), 0)

    # Check if slot touches prime hours
    return not (slot_end.time() <= p_start or slot_start.time() >= p_end)


def check_advance_window(
    slot_start: datetime,
    current_time: datetime,
    config: Dict[str, Any] = ALLOCATION_CONFIG,
) -> AllocationCheckResult:
    """Rejects bookings placed too far in the future."""
    max_days = config.get("MAX_ADVANCE_BOOKING_DAYS", 14)
    max_date = current_time + timedelta(days=max_days)

    if slot_start > max_date:
        days_ahead = (slot_start - current_time).total_seconds() / 86400.0
        return AllocationCheckResult(
            allowed=False,
            rule_name="Max Advance Window",
            reason=f"Slots can only be booked up to {max_days} days in advance (requested {days_ahead:.1f} days ahead).",
            details={"max_advance_days": max_days, "requested_advance_days": days_ahead},
        )
    return AllocationCheckResult(
        allowed=True,
        rule_name="Max Advance Window",
        reason=f"Slot is within the {max_days}-day advance window.",
    )


def check_max_active_bookings(
    active_booking_count: int,
    config: Dict[str, Any] = ALLOCATION_CONFIG,
) -> AllocationCheckResult:
    """Rejects if user already has max active (pending/approved/in-progress) bookings."""
    max_active = config.get("MAX_ACTIVE_BOOKINGS_PER_USER", 3)
    if active_booking_count >= max_active:
        return AllocationCheckResult(
            allowed=False,
            rule_name="Max Active Bookings",
            reason=f"You have reached the maximum limit of {max_active} active reservations.",
            details={"active_count": active_booking_count, "limit": max_active},
        )
    return AllocationCheckResult(
        allowed=True,
        rule_name="Max Active Bookings",
        reason=f"{active_booking_count}/{max_active} active bookings used.",
    )


def check_rolling_weekly_hours(
    recent_user_hours: float,
    requested_hours: float,
    recent_group_hours: float = 0.0,
    has_group: bool = False,
    config: Dict[str, Any] = ALLOCATION_CONFIG,
) -> AllocationCheckResult:
    """
    Ensures neither the individual user nor their team/group exceeds the 7-day rolling hour cap.
    """
    user_cap = config.get("MAX_WEEKLY_HOURS_PER_USER", 12.0)
    if recent_user_hours + requested_hours > user_cap:
        remaining = max(0.0, user_cap - recent_user_hours)
        return AllocationCheckResult(
            allowed=False,
            rule_name="User Weekly Hour Cap",
            reason=f"Exceeds weekly cap of {user_cap}h. You have used {recent_user_hours:.1f}h in the last 7 days ({remaining:.1f}h remaining).",
            details={"weekly_limit": user_cap, "used_hours": recent_user_hours, "requested_hours": requested_hours},
        )

    if has_group:
        group_cap = config.get("MAX_WEEKLY_HOURS_PER_GROUP", 24.0)
        if recent_group_hours + requested_hours > group_cap:
            remaining_g = max(0.0, group_cap - recent_group_hours)
            return AllocationCheckResult(
                allowed=False,
                rule_name="Group Weekly Hour Cap",
                reason=f"Your group has used {recent_group_hours:.1f}h of its {group_cap}h weekly cap ({remaining_g:.1f}h remaining).",
                details={"group_limit": group_cap, "group_used_hours": recent_group_hours, "requested_hours": requested_hours},
            )

    return AllocationCheckResult(
        allowed=True,
        rule_name="Weekly Hour Cap",
        reason=f"Within rolling weekly caps ({recent_user_hours + requested_hours:.1f}/{user_cap}h user).",
    )


def check_prime_slot_cooldown(
    slot_start: datetime,
    slot_end: datetime,
    last_prime_slot_end: Optional[datetime],
    config: Dict[str, Any] = ALLOCATION_CONFIG,
) -> AllocationCheckResult:
    """
    Enforces a cooldown between prime-slot bookings on the same resource
    so high-demand peak hours are equitably shared across users.
    """
    if not is_prime_slot(slot_start, slot_end, config):
        return AllocationCheckResult(
            allowed=True,
            rule_name="Prime Slot Cooldown",
            reason="Slot is outside prime hours.",
        )

    if last_prime_slot_end is None:
        return AllocationCheckResult(
            allowed=True,
            rule_name="Prime Slot Cooldown",
            reason="No recent prime slot reservations on file.",
        )

    cooldown_hours = config.get("PRIME_COOLDOWN_HOURS", 48.0)
    time_since_last = (slot_start - last_prime_slot_end).total_seconds() / 3600.0

    if time_since_last < cooldown_hours:
        remaining = cooldown_hours - time_since_last
        return AllocationCheckResult(
            allowed=False,
            rule_name="Prime Slot Cooldown",
            reason=f"Prime slot cooldown active. Please wait {remaining:.1f} more hours before booking another peak window.",
            details={"cooldown_hours": cooldown_hours, "hours_since_last": time_since_last},
        )

    return AllocationCheckResult(
        allowed=True,
        rule_name="Prime Slot Cooldown",
        reason="Cooldown period between prime slots satisfied.",
    )


def evaluate_allocation_constraints(
    current_time: datetime,
    slot_start: datetime,
    slot_end: datetime,
    active_booking_count: int,
    recent_user_hours: float,
    recent_group_hours: float = 0.0,
    has_group: bool = False,
    last_prime_slot_end: Optional[datetime] = None,
    config: Dict[str, Any] = ALLOCATION_CONFIG,
) -> Dict[str, Any]:
    """Evaluates all allocation constraints and returns pass/fail with full details."""
    requested_hours = max(0.5, (slot_end - slot_start).total_seconds() / 3600.0)

    checks = [
        check_advance_window(slot_start, current_time, config),
        check_max_active_bookings(active_booking_count, config),
        check_rolling_weekly_hours(recent_user_hours, requested_hours, recent_group_hours, has_group, config),
        check_prime_slot_cooldown(slot_start, slot_end, last_prime_slot_end, config),
    ]

    failed = [c for c in checks if not c.allowed]

    return {
        "allowed": len(failed) == 0,
        "first_rejection_reason": failed[0].reason if failed else None,
        "checks": [
            {"rule": c.rule_name, "allowed": c.allowed, "reason": c.reason, "details": c.details}
            for c in checks
        ],
    }


# ── Waitlist Scoring & Ranking ────────────────────────────────────────────────

@dataclass
class WaitlistScoreBreakdown:
    total_score: float
    purpose_priority_score: float
    first_time_user_score: float
    inverse_recent_usage_score: float
    waiting_time_score: float
    no_show_penalty: float
    explanation_summary: str
    factors: Dict[str, Any] = field(default_factory=dict)


def compute_waitlist_score(
    priority_tier: str,
    total_past_completed_bookings: int,
    recent_weekly_hours_used: float,
    waitlist_created_at: datetime,
    evaluation_time: datetime,
    strike_count: int = 0,
    config: Dict[str, Any] = ALLOCATION_CONFIG,
) -> WaitlistScoreBreakdown:
    """
    Computes a deterministic priority score for waitlist sorting:
    Score = (
        Purpose Priority
        + First-Time-User Boost
        + Inverse Recent Usage (encourages fair asset sharing)
        + Waiting-Time Bonus (anti-starvation)
        - Disciplinary Strike / No-Show Penalty
    )
    """
    # 1. Purpose Priority
    p_weights = config.get("PURPOSE_PRIORITY_WEIGHTS", {})
    purpose_score = p_weights.get(priority_tier.upper(), p_weights.get("STANDARD", 5.0))

    # 2. First-Time-User Boost
    first_time_boost = config.get("FIRST_TIME_USER_BOOST", 20.0) if total_past_completed_bookings == 0 else 0.0

    # 3. Inverse Recent Usage
    # Users with 0 hours used in the last 7 days get maximum boost; heavy users get lower
    user_cap = config.get("MAX_WEEKLY_HOURS_PER_USER", 12.0)
    unused_hours = max(0.0, user_cap - recent_weekly_hours_used)
    inv_factor = config.get("INVERSE_RECENT_USAGE_WEIGHT", 2.0)
    inverse_usage_score = round(unused_hours * inv_factor, 2)

    # 4. Waiting-Time Bonus
    hours_waited = max(0.0, (evaluation_time - waitlist_created_at).total_seconds() / 3600.0)
    hourly_rate = config.get("WAITING_TIME_HOURLY_BONUS", 1.5)
    max_wait_bonus = config.get("MAX_WAITING_BONUS", 30.0)
    waiting_time_score = round(min(max_wait_bonus, hours_waited * hourly_rate), 2)

    # 5. No-Show / Strike Penalty
    strike_penalty_rate = config.get("NO_SHOW_PENALTY_PER_STRIKE", 15.0)
    no_show_penalty = round(strike_count * strike_penalty_rate, 2)

    total_score = round(
        purpose_score + first_time_boost + inverse_usage_score + waiting_time_score - no_show_penalty,
        2,
    )

    # Explanation summary
    summary = (
        f"Score {total_score:.1f}: {priority_tier} tier (+{purpose_score}), "
        f"{'First-time booker boost (+' + str(first_time_boost) + '), ' if first_time_boost > 0 else ''}"
        f"Low recent usage (+{inverse_usage_score}), "
        f"Waited {hours_waited:.1f}h (+{waiting_time_score})"
        f"{', Disciplinary penalty (-' + str(no_show_penalty) + ')' if no_show_penalty > 0 else ''}."
    )

    return WaitlistScoreBreakdown(
        total_score=total_score,
        purpose_priority_score=purpose_score,
        first_time_user_score=first_time_boost,
        inverse_recent_usage_score=inverse_usage_score,
        waiting_time_score=waiting_time_score,
        no_show_penalty=no_show_penalty,
        explanation_summary=summary,
        factors={
            "priority_tier": priority_tier,
            "total_past_bookings": total_past_completed_bookings,
            "recent_hours_used": recent_weekly_hours_used,
            "hours_waited": round(hours_waited, 2),
            "strike_count": strike_count,
        },
    )

