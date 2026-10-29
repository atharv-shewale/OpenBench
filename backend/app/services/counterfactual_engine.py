"""
Counterfactual explainer for OpenBench bookings.

Given a rejected or waitlisted booking request, searches minimal variations
(missing certifications, shorter durations, alternative slot windows across the next 7 days)
by re-running the pure eligibility engine and conflict checks, returning concrete,
plain-English suggestions like "You'd be approved if...".
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta, time
from typing import Any, Dict, List, Optional

from app.services.eligibility_engine import (
    evaluate_booking_eligibility,
    check_credentials_rule,
    check_credits_and_deposit_rule,
)


def generate_counterfactual_explanations(
    user_data: Dict[str, Any],
    equipment_data: Dict[str, Any],
    booking_request: Dict[str, Any],
    current_time: datetime,
    existing_bookings: Optional[List[Dict[str, Any]]] = None,
) -> List[Dict[str, Any]]:
    """
    Analyzes why a booking failed or is waitlisted, and tests hypothetical adjustments:
    1. What if missing credentials are acquired?
    2. What if duration is reduced?
    3. What if the user books an alternative slot during operating hours within the next 7 days?
    4. What if credits are added?
    5. What if supervisor endorsement is attached?

    Returns a list of actionable recommendation objects with plain-language advice:
    [
        {
            "category": "duration",
            "message": "You'd be approved if you reduce your duration to 2.0 hours (saving 30 credits).",
            "suggestion": { "slot_end": "..." }
        },
        ...
    ]
    """
    suggestions: List[Dict[str, Any]] = []
    base_eval = evaluate_booking_eligibility(user_data, equipment_data, booking_request, current_time)

    slot_start: datetime = booking_request["slot_start"]
    slot_end: datetime = booking_request["slot_end"]
    original_duration = max(0.5, (slot_end - slot_start).total_seconds() / 3600.0)
    rate = equipment_data.get("credit_per_hour", 10)
    deposit = equipment_data.get("deposit_credits", 0)
    spendable = user_data.get("spendable_credits", 0)

    # ── Counterfactual 1: Missing Credentials ───────────────────────────────────
    cred_rule = next((r for r in base_eval.results if r.category == "credentials"), None)
    if cred_rule and not cred_rule.passed:
        req_creds = equipment_data.get("required_credentials") or []
        user_creds = {c.get("credential_type") for c in user_data.get("credentials") or [] if c.get("is_verified")}
        missing = [c for c in req_creds if c not in user_creds]

        if missing:
            suggestions.append({
                "type": "credential",
                "action": "complete_credential",
                "message": f"You'd be approved if you complete verification for certification '{', '.join(missing)}'.",
                "details": f"Submit your certificate or training completion proof to the lab manager for fast-track verification.",
            })

    # ── Counterfactual 2: Supervisor Sign-off ───────────────────────────────────
    super_rule = next((r for r in base_eval.results if r.category == "supervision"), None)
    if super_rule and not super_rule.passed:
        suggestions.append({
            "type": "supervision",
            "action": "request_supervisor_signoff",
            "message": "You'd be approved if a faculty mentor or lab supervisor attaches an endorsement to this request.",
            "details": "Toggle 'Supervisor Endorsement' and provide your faculty sponsor's name.",
        })

    # ── Counterfactual 3: Shorten Duration to Fit Spendable Credits ────────────
    credit_rule = next((r for r in base_eval.results if r.category == "credits"), None)
    if credit_rule and not credit_rule.passed:
        available_for_usage = spendable - deposit
        if available_for_usage > 0 and rate > 0:
            affordable_hours = available_for_usage / float(rate)
            # Try 1 hour increments or half hours
            viable_hours = int(affordable_hours)
            if viable_hours >= 1 and viable_hours < original_duration:
                new_end = slot_start + timedelta(hours=viable_hours)
                # Re-run engine to verify if shortening makes it pass
                hypo_req = {**booking_request, "slot_end": new_end}
                hypo_eval = evaluate_booking_eligibility(user_data, equipment_data, hypo_req, current_time)
                # If only credit failed before, this would work
                credit_pass_now = any(r.category == "credits" and r.passed for r in hypo_eval.results)
                if credit_pass_now:
                    suggestions.append({
                        "type": "duration",
                        "action": "shorten_duration",
                        "message": f"You'd be approved if you shorten your booking to {viable_hours} hour(s) (costs {viable_hours * rate + deposit} cr instead of {int(original_duration * rate) + deposit} cr).",
                        "suggested_slot_start": slot_start.isoformat(),
                        "suggested_slot_end": new_end.isoformat(),
                        "credits_required": viable_hours * rate + deposit,
                    })

        # Suggest exact credit top-up
        total_needed = int(original_duration * rate) + deposit
        shortfall = total_needed - spendable
        if shortfall > 0:
            suggestions.append({
                "type": "credits",
                "action": "acquire_credits",
                "message": f"You'd be approved if you add {shortfall} more credit(s) to reach the required {total_needed} credits.",
                "details": f"Earn credits by sharing idle assets, completing training courses, or requesting an institutional grant.",
            })

    # ── Counterfactual 4: Alternative Free Slots in Next 7 Days ────────────────
    # Check if slot conflict exists or if outside window
    schedule_rule = next((r for r in base_eval.results if r.category == "schedule"), None)
    is_conflicted = False
    if existing_bookings:
        for b in existing_bookings:
            b_start = b["slot_start"]
            b_end = b["slot_end"]
            if b_start < slot_end and b_end > slot_start:
                is_conflicted = True
                break

    if (schedule_rule and not schedule_rule.passed) or is_conflicted:
        alt_slots = find_alternative_slots(
            user_data=user_data,
            equipment_data=equipment_data,
            target_duration_hours=original_duration,
            search_from=max(current_time, slot_start),
            existing_bookings=existing_bookings or [],
            max_results=3,
        )
        for alt in alt_slots:
            suggestions.append({
                "type": "alternative_slot",
                "action": "reschedule_slot",
                "message": f"Alternative slot open on {alt['slot_start'].strftime('%A, %b %d at %H:%M')}.",
                "suggested_slot_start": alt["slot_start"].isoformat(),
                "suggested_slot_end": alt["slot_end"].isoformat(),
                "details": f"Guaranteed free slot within lab operating hours ({alt['duration_hours']} hours).",
            })

    return suggestions


def find_alternative_slots(
    user_data: Dict[str, Any],
    equipment_data: Dict[str, Any],
    target_duration_hours: float,
    search_from: datetime,
    existing_bookings: List[Dict[str, Any]],
    max_results: int = 3,
) -> List[Dict[str, Any]]:
    """
    Searches the next 7 days for slots that match operating windows
    and do not conflict with existing approved bookings.
    """
    alternatives = []
    windows = equipment_data.get("availability_windows") or []
    # If no windows, default to weekdays 09:00 - 17:00
    if not windows:
        windows = [{"day_of_week": d, "start_time": "09:00", "end_time": "17:00"} for d in range(5)]

    # Search up to 7 days ahead
    current_day = search_from.date()
    for day_offset in range(1, 8):
        candidate_date = current_day + timedelta(days=day_offset)
        dow = candidate_date.weekday()

        day_windows = [w for w in windows if w.get("day_of_week") == dow]
        for w in day_windows:
            try:
                sh, sm = map(int, w["start_time"].split(":")[:2])
                eh, em = map(int, w["end_time"].split(":")[:2])
                window_start = datetime.combine(candidate_date, time(sh, sm))
                window_end = datetime.combine(candidate_date, time(eh, em))

                # Step through window in 2-hour or target_duration chunks
                slot_candidate_start = window_start
                slot_candidate_end = slot_candidate_start + timedelta(hours=target_duration_hours)

                while slot_candidate_end <= window_end:
                    # Check conflict
                    has_conflict = False
                    for ex in existing_bookings:
                        ex_start = ex["slot_start"]
                        ex_end = ex["slot_end"]
                        if ex_start < slot_candidate_end and ex_end > slot_candidate_start:
                            has_conflict = True
                            break

                    if not has_conflict:
                        alternatives.append({
                            "slot_start": slot_candidate_start,
                            "slot_end": slot_candidate_end,
                            "duration_hours": target_duration_hours,
                        })
                        if len(alternatives) >= max_results:
                            return alternatives

                    slot_candidate_start += timedelta(hours=1)
                    slot_candidate_end = slot_candidate_start + timedelta(hours=target_duration_hours)
            except Exception:
                continue

    return alternatives
