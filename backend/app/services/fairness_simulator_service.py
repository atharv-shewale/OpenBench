"""
Fairness simulator service — deterministic synthetic demand replay.

Compares First-Come-First-Served (FCFS) against the OpenBench Policy over a
30-day synthetic demand stream (seeded RNG). Computes:
1. Gini coefficient of allocated hours per user
2. Average wait time before obtaining access
3. Share of first-time users served
4. Lab utilisation rate

ALL DATA GENERATED IS SYNTHETIC AND ADVISORY FOR POLICY EVALUATION.
"""
from __future__ import annotations

import random
from dataclasses import dataclass
from typing import Any, Dict, List, Tuple


def calculate_gini(values: List[float]) -> float:
    """
    Computes the Gini coefficient for a list of non-negative values.
    G = sum_i sum_j |x_i - x_j| / (2 * n * sum_i x_i)
    Returns a value between 0.0 (perfect equality) and 1.0 (extreme inequality).
    """
    n = len(values)
    if n == 0:
        return 0.0
    total = sum(values)
    if total == 0:
        return 0.0

    sorted_vals = sorted(values)
    diff_sum = sum(
        abs(sorted_vals[i] - sorted_vals[j])
        for i in range(n)
        for j in range(n)
    )
    return round(diff_sum / (2.0 * n * total), 4)


@dataclass
class SyntheticUser:
    id: int
    name: str
    archetype: str  # power_user, apprentice_msme, student, occasional
    is_first_time: bool
    weekly_cap: float = 10.0


@dataclass
class SyntheticRequest:
    id: int
    user_id: int
    machine_id: int
    day: int           # 1 to 30
    start_hour: int    # 9 to 18 (e.g. 9 to 13)
    duration_hours: int  # 1 to 4
    purpose: str       # SAFETY_CRITICAL, STUDENT_PROJECT, COMMERCIAL, ROUTINE
    submitted_day: int # submission day (lead time)
    submitted_hour: int


def generate_synthetic_demand(seed: int = 42, days: int = 30) -> Tuple[List[SyntheticUser], List[SyntheticRequest]]:
    """
    Deterministically generates synthetic users and booking requests over `days`
    using a fixed seed with peak contention.
    """
    rng = random.Random(seed)

    # 40 Synthetic Users
    users: List[SyntheticUser] = []

    # 8 Power Users / Veteran Labs (book 7-15 days ahead, heavy 3-4 hr requests)
    for i in range(1, 9):
        users.append(SyntheticUser(
            id=i,
            name=f"Senior Lab Researcher #{i}",
            archetype="power_user",
            is_first_time=False,
            weekly_cap=10.0,
        ))

    # 20 ITI Apprentices & Micro MSMEs (first-time applicants, 1-3 days ahead)
    for i in range(9, 29):
        users.append(SyntheticUser(
            id=i,
            name=f"MSME / ITI Apprentice #{i}",
            archetype="apprentice_msme",
            is_first_time=True,
            weekly_cap=10.0,
        ))

    # 12 Student Project Teams
    for i in range(29, 41):
        users.append(SyntheticUser(
            id=i,
            name=f"Student Project Team #{i}",
            archetype="student",
            is_first_time=True if i > 34 else False,
            weekly_cap=10.0,
        ))

    # 3 High-value bottleneck machines (e.g. Universal Testing Machine, CNC Lathe, Laser Cutter)
    machine_count = 3
    requests: List[SyntheticRequest] = []
    req_id = 1

    for day in range(1, days + 1):
        # Power users flood requests early with 7-14 days lead time
        for pu in users[:8]:
            if rng.random() < 0.60:
                machine_id = rng.randint(1, machine_count)
                lead_days = rng.randint(6, 14)
                submitted_day = max(1, day - lead_days)
                duration = rng.choice([3, 4, 4])
                start_hour = rng.choice([10, 11, 13, 14])  # prime hours
                requests.append(SyntheticRequest(
                    id=req_id,
                    user_id=pu.id,
                    machine_id=machine_id,
                    day=day,
                    start_hour=start_hour,
                    duration_hours=duration,
                    purpose=rng.choice(["COMMERCIAL", "ROUTINE"]),
                    submitted_day=submitted_day,
                    submitted_hour=rng.randint(8, 12),
                ))
                req_id += 1

        # MSMEs & Apprentices apply 1-3 days ahead as fabrication needs arise
        for msme in users[8:28]:
            if rng.random() < 0.35:
                machine_id = rng.randint(1, machine_count)
                lead_days = rng.randint(1, 3)
                submitted_day = max(1, day - lead_days)
                duration = rng.choice([2, 3])
                start_hour = rng.choice([10, 11, 13, 14, 15])
                requests.append(SyntheticRequest(
                    id=req_id,
                    user_id=msme.id,
                    machine_id=machine_id,
                    day=day,
                    start_hour=start_hour,
                    duration_hours=duration,
                    purpose=rng.choice(["SAFETY_CRITICAL", "COMMERCIAL"]),
                    submitted_day=submitted_day,
                    submitted_hour=rng.randint(9, 17),
                ))
                req_id += 1

        # Students apply 3-5 days ahead
        for st in users[28:40]:
            if rng.random() < 0.30:
                machine_id = rng.randint(1, machine_count)
                lead_days = rng.randint(2, 5)
                submitted_day = max(1, day - lead_days)
                duration = rng.choice([2, 3])
                start_hour = rng.choice([9, 10, 14, 15])
                requests.append(SyntheticRequest(
                    id=req_id,
                    user_id=st.id,
                    machine_id=machine_id,
                    day=day,
                    start_hour=start_hour,
                    duration_hours=duration,
                    purpose="STUDENT_PROJECT",
                    submitted_day=submitted_day,
                    submitted_hour=rng.randint(10, 16),
                ))
                req_id += 1

    return users, requests


def simulate_fcfs(
    users: List[SyntheticUser],
    requests: List[SyntheticRequest],
    days: int = 30,
    machine_count: int = 3,
) -> Dict[str, Any]:
    """
    Replay Policy 1: First-Come, First-Served (FCFS).
    Requests are evaluated strictly in order of submission time.
    No hour caps, no first-time boosts, no waitlist scoring.
    """
    # Sort requests by submission time: (submitted_day, submitted_hour, id)
    sorted_reqs = sorted(requests, key=lambda r: (r.submitted_day, r.submitted_hour, r.id))

    # Grid of machine occupancy: (machine_id, day, hour) -> user_id
    schedule: Dict[Tuple[int, int, int], int] = {}

    user_hours: Dict[int, float] = {u.id: 0.0 for u in users}
    first_time_served: Dict[int, bool] = {u.id: False for u in users if u.is_first_time}
    wait_times: List[float] = []

    approved_count = 0
    daily_hours_delivered: Dict[int, float] = {d: 0.0 for d in range(1, days + 1)}

    for req in sorted_reqs:
        # Check if slot is completely free (operating hours 09:00 - 17:00 = 8 hrs)
        can_fit = True
        for h in range(req.start_hour, req.start_hour + req.duration_hours):
            if h >= 17:  # lab closes at 17:00
                can_fit = False
                break
            if (req.machine_id, req.day, h) in schedule:
                can_fit = False
                break

        if can_fit:
            # Approve slot
            for h in range(req.start_hour, req.start_hour + req.duration_hours):
                schedule[(req.machine_id, req.day, h)] = req.user_id

            user_hours[req.user_id] += req.duration_hours
            daily_hours_delivered[req.day] += req.duration_hours
            approved_count += 1

            if req.user_id in first_time_served:
                first_time_served[req.user_id] = True

            wait_days = max(0, req.day - req.submitted_day)
            wait_times.append(wait_days * 24.0)
        else:
            # Under raw FCFS without waitlist promotion, conflicting requests are rejected or wait indefinitely
            wait_times.append(72.0)  # 3 days wait penalty

    # Calculate metrics
    gini = calculate_gini(list(user_hours.values()))
    avg_wait = round(sum(wait_times) / max(1, len(wait_times)), 1)

    ft_total = len(first_time_served)
    ft_served = sum(1 for v in first_time_served.values() if v)
    ft_pct = round((ft_served / max(1, ft_total)) * 100.0, 1)

    total_capacity_hours = days * machine_count * 8  # 8 operational hours/day (9-17)
    total_delivered = sum(user_hours.values())
    utilisation_pct = round((total_delivered / max(1, total_capacity_hours)) * 100.0, 1)

    sorted_user_allocations = sorted([
        {"user_id": u.id, "name": u.name, "archetype": u.archetype, "hours": user_hours[u.id]}
        for u in users
    ], key=lambda x: x["hours"], reverse=True)

    quintiles = []
    bucket_size = len(users) // 5
    for q in range(5):
        chunk = sorted_user_allocations[q * bucket_size:(q + 1) * bucket_size]
        q_hours = sum(c["hours"] for c in chunk)
        quintiles.append({
            "quintile": f"Top {(q)*20}-{(q+1)*20}%",
            "hours": round(q_hours, 1),
            "share_pct": round((q_hours / max(1, total_delivered)) * 100.0, 1),
        })

    daily_util = [
        {
            "day": d,
            "hours": round(daily_hours_delivered[d], 1),
            "utilisation_pct": round((daily_hours_delivered[d] / (machine_count * 8)) * 100.0, 1),
        }
        for d in range(1, days + 1)
    ]

    return {
        "policy_name": "First-Come, First-Served (FCFS)",
        "gini_coefficient": gini,
        "average_wait_hours": avg_wait,
        "first_time_users_served_pct": ft_pct,
        "utilisation_pct": utilisation_pct,
        "total_hours_delivered": round(total_delivered, 1),
        "total_requests_approved": approved_count,
        "total_requests_submitted": len(requests),
        "hours_per_user_buckets": quintiles,
        "daily_utilisation": daily_util,
    }


def simulate_openbench(
    users: List[SyntheticUser],
    requests: List[SyntheticRequest],
    days: int = 30,
    machine_count: int = 3,
) -> Dict[str, Any]:
    """
    Replay Policy 2: OpenBench Dynamic Allocation Policy.
    Features:
    - 10-hour rolling weekly cap per user.
    - Dynamic priority scoring: purpose tier + first-time boost (+30 pts) +
      inverse recent usage bonus - repeat prime slot penalty.
    - Waitlist auto-promotion to backfill unbooked slots and cancellations.
    """
    schedule: Dict[Tuple[int, int, int], int] = {}
    user_hours: Dict[int, float] = {u.id: 0.0 for u in users}
    user_weekly_hours: Dict[Tuple[int, int], float] = {}  # (user_id, week_num) -> hours
    first_time_served: Dict[int, bool] = {u.id: False for u in users if u.is_first_time}
    wait_times: List[float] = []

    approved_count = 0
    daily_hours_delivered: Dict[int, float] = {d: 0.0 for d in range(1, days + 1)}

    purpose_weights = {
        "SAFETY_CRITICAL": 35.0,
        "STUDENT_PROJECT": 25.0,
        "COMMERCIAL": 20.0,
        "ROUTINE": 10.0,
    }

    unfulfilled_waitlist: List[SyntheticRequest] = []

    for day in range(1, days + 1):
        week_num = (day - 1) // 7

        pending_today = [r for r in requests if r.day == day and r.submitted_day <= day]
        active_candidates = unfulfilled_waitlist + pending_today
        unfulfilled_waitlist = []

        scored_candidates = []
        for req in active_candidates:
            user = next(u for u in users if u.id == req.user_id)
            current_week_hrs = user_weekly_hours.get((user.id, week_num), 0.0)

            is_capped = (current_week_hrs + req.duration_hours) > user.weekly_cap

            score = purpose_weights.get(req.purpose, 15.0)

            # First-time user boost (+35)
            if user.is_first_time and not first_time_served.get(user.id, False):
                score += 35.0

            # Inverse recent usage bonus: users with lower usage get +25 pts
            unused_allowance = max(0.0, user.weekly_cap - current_week_hrs)
            score += min(25.0, unused_allowance * 2.5)

            # Prime slot cooldown penalty
            if req.start_hour in [13, 14, 15] and current_week_hrs > 6.0:
                score -= 20.0

            if is_capped:
                score -= 75.0

            scored_candidates.append((score, req))

        scored_candidates.sort(key=lambda x: x[0], reverse=True)

        for score, req in scored_candidates:
            user = next(u for u in users if u.id == req.user_id)
            current_week_hrs = user_weekly_hours.get((user.id, week_num), 0.0)

            can_fit = True
            for h in range(req.start_hour, req.start_hour + req.duration_hours):
                if h >= 17 or (req.machine_id, req.day, h) in schedule:
                    can_fit = False
                    break

            if (current_week_hrs + req.duration_hours) > user.weekly_cap and score < 15.0:
                unfulfilled_waitlist.append(req)
                continue

            if can_fit:
                for h in range(req.start_hour, req.start_hour + req.duration_hours):
                    schedule[(req.machine_id, req.day, h)] = req.user_id

                user_hours[req.user_id] += req.duration_hours
                user_weekly_hours[(user.id, week_num)] = current_week_hrs + req.duration_hours
                daily_hours_delivered[req.day] += req.duration_hours
                approved_count += 1

                if req.user_id in first_time_served:
                    first_time_served[req.user_id] = True

                wait_days = max(0, day - req.submitted_day)
                wait_times.append(wait_days * 24.0)
            else:
                # Small counterfactual gap fill: +/- 1 hour
                shifted = False
                for delta in [-1, 1, -2]:
                    shifted_start = req.start_hour + delta
                    if 9 <= shifted_start and (shifted_start + req.duration_hours) <= 17:
                        shifted_fit = all(
                            (req.machine_id, req.day, sh) not in schedule
                            for sh in range(shifted_start, shifted_start + req.duration_hours)
                        )
                        if shifted_fit:
                            for sh in range(shifted_start, shifted_start + req.duration_hours):
                                schedule[(req.machine_id, req.day, sh)] = req.user_id

                            user_hours[req.user_id] += req.duration_hours
                            user_weekly_hours[(user.id, week_num)] = current_week_hrs + req.duration_hours
                            daily_hours_delivered[req.day] += req.duration_hours
                            approved_count += 1

                            if req.user_id in first_time_served:
                                first_time_served[req.user_id] = True

                            wait_days = max(0, day - req.submitted_day)
                            wait_times.append(wait_days * 24.0)
                            shifted = True
                            break

                if not shifted:
                    if day < days:
                        req.day = day + 1
                        unfulfilled_waitlist.append(req)
                    else:
                        wait_times.append(36.0)

    gini = calculate_gini(list(user_hours.values()))
    avg_wait = round(sum(wait_times) / max(1, len(wait_times)), 1)

    ft_total = len(first_time_served)
    ft_served = sum(1 for v in first_time_served.values() if v)
    ft_pct = round((ft_served / max(1, ft_total)) * 100.0, 1)

    total_capacity_hours = days * machine_count * 8
    total_delivered = sum(user_hours.values())
    utilisation_pct = round((total_delivered / max(1, total_capacity_hours)) * 100.0, 1)

    sorted_user_allocations = sorted([
        {"user_id": u.id, "name": u.name, "archetype": u.archetype, "hours": user_hours[u.id]}
        for u in users
    ], key=lambda x: x["hours"], reverse=True)

    quintiles = []
    bucket_size = len(users) // 5
    for q in range(5):
        chunk = sorted_user_allocations[q * bucket_size:(q + 1) * bucket_size]
        q_hours = sum(c["hours"] for c in chunk)
        quintiles.append({
            "quintile": f"Top {(q)*20}-{(q+1)*20}%",
            "hours": round(q_hours, 1),
            "share_pct": round((q_hours / max(1, total_delivered)) * 100.0, 1),
        })

    daily_util = [
        {
            "day": d,
            "hours": round(daily_hours_delivered[d], 1),
            "utilisation_pct": round((daily_hours_delivered[d] / (machine_count * 8)) * 100.0, 1),
        }
        for d in range(1, days + 1)
    ]

    return {
        "policy_name": "OpenBench Dynamic Allocation Policy",
        "gini_coefficient": gini,
        "average_wait_hours": avg_wait,
        "first_time_users_served_pct": ft_pct,
        "utilisation_pct": utilisation_pct,
        "total_hours_delivered": round(total_delivered, 1),
        "total_requests_approved": approved_count,
        "total_requests_submitted": len(requests),
        "hours_per_user_buckets": quintiles,
        "daily_utilisation": daily_util,
    }


def run_fairness_simulation(seed: int = 42, days: int = 30) -> Dict[str, Any]:
    """
    Executes a side-by-side comparison between First-Come-First-Served and
    the OpenBench allocation policy on a deterministic synthetic demand stream.
    """
    users, requests = generate_synthetic_demand(seed=seed, days=days)

    fcfs_results = simulate_fcfs(users, requests, days=days)
    openbench_results = simulate_openbench(users, requests, days=days)

    gini_improvement = round(
        ((fcfs_results["gini_coefficient"] - openbench_results["gini_coefficient"])
         / max(0.01, fcfs_results["gini_coefficient"])) * 100.0, 1
    )
    first_time_multiplier = round(
        openbench_results["first_time_users_served_pct"] / max(0.1, fcfs_results["first_time_users_served_pct"]), 2
    )
    wait_reduction_pct = round(
        ((fcfs_results["average_wait_hours"] - openbench_results["average_wait_hours"])
         / max(0.1, fcfs_results["average_wait_hours"])) * 100.0, 1
    )

    return {
        "is_synthetic": True,
        "notice": "SYNTHETIC DEMAND REPLAY (SEEDED SIMULATION) — Advisory and educational demonstration of allocation fairness.",
        "seed": seed,
        "days_simulated": days,
        "total_synthetic_users": len(users),
        "total_synthetic_requests": len(requests),
        "fcfs_metrics": fcfs_results,
        "openbench_metrics": openbench_results,
        "comparison_summary": {
            "gini_improvement_pct": gini_improvement,
            "first_time_served_multiplier": first_time_multiplier,
            "wait_reduction_pct": wait_reduction_pct,
            "openbench_gini": openbench_results["gini_coefficient"],
            "fcfs_gini": fcfs_results["gini_coefficient"],
            "conclusion": (
                f"Under OpenBench, the Gini coefficient improved by {gini_improvement}% "
                f"(from {fcfs_results['gini_coefficient']} to {openbench_results['gini_coefficient']}), "
                f"serving {first_time_multiplier}x more first-time MSMEs and apprentices while maintaining "
                f"{openbench_results['utilisation_pct']}% lab capacity utilisation."
            ),
        },
    }
