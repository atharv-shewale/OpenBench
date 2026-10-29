"""
Comprehensive worked-example unit tests for the allocation engine and waitlist ranking.
"""
from datetime import datetime, timedelta, time
import pytest

from app.services.allocation_engine import (
    ALLOCATION_CONFIG,
    is_prime_slot,
    check_advance_window,
    check_max_active_bookings,
    check_rolling_weekly_hours,
    check_prime_slot_cooldown,
    compute_waitlist_score,
    evaluate_allocation_constraints,
)


class TestAllocationConstraints:
    @property
    def fixed_now(self):
        return datetime(2026, 10, 30, 10, 0, 0)

    # ── 1. Rolling Weekly Hour Cap (User and Group) ────────────────────────────
    def test_rolling_weekly_hour_cap_user_allowed(self):
        # 8h used + 3h requested = 11h (cap is 12h) -> Passes
        res = check_rolling_weekly_hours(recent_user_hours=8.0, requested_hours=3.0)
        assert res.allowed is True
        assert "within rolling weekly caps" in res.reason.lower()

    def test_rolling_weekly_hour_cap_user_exceeded(self):
        # 10h used + 3h requested = 13h (cap is 12h) -> Fails with remaining amount shown
        res = check_rolling_weekly_hours(recent_user_hours=10.0, requested_hours=3.0)
        assert res.allowed is False
        assert "exceeds weekly cap of 12" in res.reason.lower()
        assert "2.0h remaining" in res.reason

    def test_rolling_weekly_hour_cap_group_exceeded(self):
        # User has only 2h used, but team/group has 23h used + 2h requested = 25h (group cap is 24h)
        res = check_rolling_weekly_hours(
            recent_user_hours=2.0,
            requested_hours=2.0,
            recent_group_hours=23.0,
            has_group=True,
        )
        assert res.allowed is False
        assert "group has used 23.0h of its 24" in res.reason.lower()

    # ── 2. Max Active Bookings ────────────────────────────────────────────────
    def test_max_active_bookings_limit(self):
        # Limit is 3 active reservations
        assert check_max_active_bookings(2).allowed is True
        res_fail = check_max_active_bookings(3)
        assert res_fail.allowed is False
        assert "maximum limit of 3" in res_fail.reason.lower()

    # ── 3. Max Advance Booking Window ─────────────────────────────────────────
    def test_max_advance_booking_window(self):
        # Max advance is 14 days
        slot_10_days = self.fixed_now + timedelta(days=10)
        assert check_advance_window(slot_10_days, self.fixed_now).allowed is True

        slot_18_days = self.fixed_now + timedelta(days=18)
        res_fail = check_advance_window(slot_18_days, self.fixed_now)
        assert res_fail.allowed is False
        assert "only be booked up to 14 days" in res_fail.reason.lower()

    # ── 4. Prime-Slot Cooldown ────────────────────────────────────────────────
    def test_prime_slot_detection(self):
        # Prime hours are 13:00 to 17:00
        prime_slot_start = datetime(2026, 10, 30, 14, 0, 0)
        prime_slot_end = datetime(2026, 10, 30, 16, 0, 0)
        assert is_prime_slot(prime_slot_start, prime_slot_end) is True

        morning_start = datetime(2026, 10, 30, 9, 0, 0)
        morning_end = datetime(2026, 10, 30, 12, 0, 0)
        assert is_prime_slot(morning_start, morning_end) is False

    def test_prime_slot_cooldown_enforced(self):
        # User finished a prime slot 20 hours ago; cooldown is 48 hours
        last_prime_end = self.fixed_now - timedelta(hours=20)
        prime_req_start = self.fixed_now + timedelta(hours=4)  # 14:00 (prime)
        prime_req_end = self.fixed_now + timedelta(hours=6)

        res = check_prime_slot_cooldown(prime_req_start, prime_req_end, last_prime_end)
        assert res.allowed is False
        assert "prime slot cooldown active" in res.reason.lower()

        # If 50 hours have elapsed (>48h cooldown), allowed
        old_prime_end = self.fixed_now - timedelta(hours=50)
        assert check_prime_slot_cooldown(prime_req_start, prime_req_end, old_prime_end).allowed is True


class TestWaitlistWorkedExamples:
    @property
    def fixed_now(self):
        return datetime(2026, 10, 30, 12, 0, 0)

    def test_first_time_user_emergency_worked_example(self):
        """
        Worked Example A:
        - Priority tier: EMERGENCY (40 pts)
        - First time user: 0 prior bookings (+20 pts)
        - 0 recent hours used out of 12 cap (+24 pts: 12 * 2.0)
        - Waited 2 hours (+3 pts: 2 * 1.5)
        - 0 strikes (-0 pts)
        Total Expected = 40 + 20 + 24 + 3 = 87.0
        """
        created_at = self.fixed_now - timedelta(hours=2)
        score = compute_waitlist_score(
            priority_tier="EMERGENCY",
            total_past_completed_bookings=0,
            recent_weekly_hours_used=0.0,
            waitlist_created_at=created_at,
            evaluation_time=self.fixed_now,
            strike_count=0,
        )

        assert score.purpose_priority_score == 40.0
        assert score.first_time_user_score == 20.0
        assert score.inverse_recent_usage_score == 24.0
        assert score.waiting_time_score == 3.0
        assert score.no_show_penalty == 0.0
        assert score.total_score == 87.0
        assert "EMERGENCY tier (+40" in score.explanation_summary
        assert "First-time booker boost (+20.0)" in score.explanation_summary

    def test_heavy_user_with_strikes_worked_example(self):
        """
        Worked Example B:
        - Priority tier: STANDARD (5 pts)
        - Repeat user: 5 prior bookings (+0 pts)
        - Heavy usage: 10 hours used out of 12 cap -> 2 unused * 2.0 = +4.0 pts
        - Waited 4 hours: 4 * 1.5 = +6.0 pts
        - 1 disciplinary strike: 1 * 15.0 = -15.0 pts
        Total Expected = 5 + 0 + 4.0 + 6.0 - 15.0 = 0.0
        """
        created_at = self.fixed_now - timedelta(hours=4)
        score = compute_waitlist_score(
            priority_tier="STANDARD",
            total_past_completed_bookings=5,
            recent_weekly_hours_used=10.0,
            waitlist_created_at=created_at,
            evaluation_time=self.fixed_now,
            strike_count=1,
        )

        assert score.purpose_priority_score == 5.0
        assert score.first_time_user_score == 0.0
        assert score.inverse_recent_usage_score == 4.0
        assert score.waiting_time_score == 6.0
        assert score.no_show_penalty == 15.0
        assert score.total_score == 0.0
        assert "Disciplinary penalty (-15.0)" in score.explanation_summary

    def test_research_priority_ranking_comparison(self):
        """
        Verify that between two users waiting for the same slot:
        User 1 (Research, 1st time, 0 strikes) outranks User 2 (Standard, repeat user).
        """
        created = self.fixed_now - timedelta(hours=1)

        user1_score = compute_waitlist_score(
            priority_tier="RESEARCH",
            total_past_completed_bookings=0,
            recent_weekly_hours_used=0.0,
            waitlist_created_at=created,
            evaluation_time=self.fixed_now,
            strike_count=0,
        )

        user2_score = compute_waitlist_score(
            priority_tier="STANDARD",
            total_past_completed_bookings=4,
            recent_weekly_hours_used=6.0,
            waitlist_created_at=created,
            evaluation_time=self.fixed_now,
            strike_count=0,
        )

        assert user1_score.total_score > user2_score.total_score
        assert user1_score.total_score == (25.0 + 20.0 + 24.0 + 1.5)  # 70.5
        assert user2_score.total_score == (5.0 + 0.0 + 12.0 + 1.5)   # 18.5

