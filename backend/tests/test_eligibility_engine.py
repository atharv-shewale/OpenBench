"""
Unit tests for the pure eligibility engine and counterfactual generator.
"""
from datetime import datetime, timedelta, time
import pytest

from app.services.eligibility_engine import (
    check_credentials_rule,
    check_account_standing_rule,
    check_supervisor_signoff_rule,
    check_credits_and_deposit_rule,
    check_slot_window_rule,
    evaluate_booking_eligibility,
)
from app.services.counterfactual_engine import (
    generate_counterfactual_explanations,
    find_alternative_slots,
)


class TestPureEligibilityRules:
    @property
    def fixed_now(self):
        return datetime(2026, 10, 30, 10, 0, 0)

    # ── Rule 1: Credentials & Expiry ───────────────────────────────────────────
    def test_credentials_none_required(self):
        res = check_credentials_rule([], [], self.fixed_now)
        assert res.passed is True
        assert res.category == "credentials"

    def test_credentials_passed_when_verified_and_unexpired(self):
        user_creds = [
            {
                "credential_type": "LASER_SAFETY_L1",
                "is_verified": True,
                "expires_at": self.fixed_now + timedelta(days=30),
            }
        ]
        res = check_credentials_rule(["LASER_SAFETY_L1"], user_creds, self.fixed_now)
        assert res.passed is True

    def test_credentials_fails_when_expired(self):
        user_creds = [
            {
                "credential_type": "LASER_SAFETY_L1",
                "is_verified": True,
                "expires_at": self.fixed_now - timedelta(days=1),  # Expired yesterday
            }
        ]
        res = check_credentials_rule(["LASER_SAFETY_L1"], user_creds, self.fixed_now)
        assert res.passed is False
        assert "expired" in res.reason.lower()

    def test_credentials_fails_when_unverified(self):
        user_creds = [
            {
                "credential_type": "CNC_OPERATOR",
                "is_verified": False,
                "expires_at": None,
            }
        ]
        res = check_credentials_rule(["CNC_OPERATOR"], user_creds, self.fixed_now)
        assert res.passed is False
        assert "pending verification" in res.reason.lower()

    # ── Rule 2: Account Standing & Role ────────────────────────────────────────
    def test_account_standing_fails_if_inactive(self):
        res = check_account_standing_rule(is_active=False, strike_count=0, user_role="user")
        assert res.passed is False
        assert "deactivated" in res.reason.lower()

    def test_account_standing_fails_at_strike_limit(self):
        res = check_account_standing_rule(is_active=True, strike_count=3, user_role="user")
        assert res.passed is False
        assert "suspended" in res.reason.lower()

    def test_role_mismatch_fails(self):
        res = check_account_standing_rule(
            is_active=True, strike_count=0, user_role="user", allowed_roles=["manager", "admin"]
        )
        assert res.passed is False
        assert "requires one of these roles" in res.reason.lower()

    # ── Rule 3: Supervisor Sign-off ───────────────────────────────────────────
    def test_supervisor_required_but_missing(self):
        res = check_supervisor_signoff_rule(
            requires_supervisor=True, has_supervisor_signoff=False
        )
        assert res.passed is False
        assert "supervisor endorsement" in res.reason.lower()

    def test_supervisor_required_and_present(self):
        res = check_supervisor_signoff_rule(
            requires_supervisor=True, has_supervisor_signoff=True, supervisor_name="Dr. Banner"
        )
        assert res.passed is True
        assert "Dr. Banner" in res.reason

    # ── Rule 4: Credits & Deposit ─────────────────────────────────────────────
    def test_credits_sufficient(self):
        # 2 hours at 15 cr/hr + 10 cr deposit = 40 needed
        res = check_credits_and_deposit_rule(
            spendable_credits=50, duration_hours=2.0, credit_per_hour=15, deposit_credits=10
        )
        assert res.passed is True
        assert "50 cr" in res.reason

    def test_credits_insufficient(self):
        # 3 hours at 20 cr/hr + 0 deposit = 60 needed
        res = check_credits_and_deposit_rule(
            spendable_credits=40, duration_hours=3.0, credit_per_hour=20, deposit_credits=0
        )
        assert res.passed is False
        assert "short by 20 cr" in res.reason.lower()

    # ── Rule 5: Slot Window & Duration ────────────────────────────────────────
    def test_slot_window_within_hours(self):
        # Friday 10:00 to 12:00
        start = datetime(2026, 10, 30, 10, 0, 0)
        end = datetime(2026, 10, 30, 12, 0, 0)
        windows = [{"day_of_week": 4, "start_time": "09:00", "end_time": "17:00"}]
        res = check_slot_window_rule(start, end, max_booking_hours=4, availability_windows=windows)
        assert res.passed is True

    def test_slot_window_closed_day(self):
        # Sunday slot
        start = datetime(2026, 11, 1, 10, 0, 0)
        end = datetime(2026, 11, 1, 12, 0, 0)
        windows = [{"day_of_week": 4, "start_time": "09:00", "end_time": "17:00"}]
        res = check_slot_window_rule(start, end, max_booking_hours=4, availability_windows=windows)
        assert res.passed is False
        assert "closed on sundays" in res.reason.lower()


class TestCounterfactualExplainer:
    def test_explains_missing_credential(self):
        now = datetime(2026, 10, 30, 10, 0, 0)
        user_data = {
            "is_active": True,
            "strike_count": 0,
            "role": "user",
            "spendable_credits": 100,
            "credentials": [],
        }
        equipment_data = {
            "credit_per_hour": 10,
            "deposit_credits": 0,
            "max_booking_hours": 4,
            "required_credentials": ["LASER_SAFETY_L1"],
            "rules": {},
            "availability_windows": [{"day_of_week": 4, "start_time": "09:00", "end_time": "17:00"}],
        }
        booking_req = {
            "slot_start": datetime(2026, 10, 30, 11, 0, 0),
            "slot_end": datetime(2026, 10, 30, 13, 0, 0),
            "has_supervisor_signoff": False,
        }

        suggestions = generate_counterfactual_explanations(
            user_data, equipment_data, booking_req, now
        )
        assert len(suggestions) > 0
        cred_sugg = next(s for s in suggestions if s["type"] == "credential")
        assert "LASER_SAFETY_L1" in cred_sugg["message"]
        assert "You'd be approved if" in cred_sugg["message"]

    def test_explains_shortening_duration_to_afford_credits(self):
        now = datetime(2026, 10, 30, 10, 0, 0)
        user_data = {
            "is_active": True,
            "strike_count": 0,
            "role": "user",
            "spendable_credits": 25,  # Has 25 credits
            "credentials": [],
        }
        equipment_data = {
            "credit_per_hour": 10,
            "deposit_credits": 5,  # Deposit 5, rate 10/hr
            "max_booking_hours": 4,
            "required_credentials": [],
            "rules": {},
            "availability_windows": [{"day_of_week": 4, "start_time": "09:00", "end_time": "17:00"}],
        }
        # Requests 3 hours: 3*10 + 5 = 35 cr (fails with 25 cr)
        # But 2 hours: 2*10 + 5 = 25 cr (fits exactly!)
        booking_req = {
            "slot_start": datetime(2026, 10, 30, 11, 0, 0),
            "slot_end": datetime(2026, 10, 30, 14, 0, 0),
            "has_supervisor_signoff": False,
        }

        suggestions = generate_counterfactual_explanations(
            user_data, equipment_data, booking_req, now
        )
        duration_sugg = next((s for s in suggestions if s["type"] == "duration"), None)
        assert duration_sugg is not None
        assert "shorten your booking to 2 hour(s)" in duration_sugg["message"]
        assert duration_sugg["credits_required"] == 25

    def test_explains_alternative_slots_on_conflict(self):
        now = datetime(2026, 10, 30, 10, 0, 0)
        user_data = {
            "is_active": True,
            "strike_count": 0,
            "role": "user",
            "spendable_credits": 100,
            "credentials": [],
        }
        equipment_data = {
            "credit_per_hour": 10,
            "deposit_credits": 0,
            "max_booking_hours": 4,
            "required_credentials": [],
            "rules": {},
            "availability_windows": [
                {"day_of_week": d, "start_time": "09:00", "end_time": "17:00"} for d in range(5)
            ],
        }
        # Requested Friday 11:00 - 13:00, which has an existing booking conflict
        req_start = datetime(2026, 10, 30, 11, 0, 0)
        req_end = datetime(2026, 10, 30, 13, 0, 0)
        existing = [{"slot_start": req_start, "slot_end": req_end}]

        suggestions = generate_counterfactual_explanations(
            user_data,
            equipment_data,
            {"slot_start": req_start, "slot_end": req_end, "has_supervisor_signoff": False},
            now,
            existing_bookings=existing,
        )
        alt_sugg = [s for s in suggestions if s["type"] == "alternative_slot"]
        assert len(alt_sugg) > 0
        assert "Alternative slot open on" in alt_sugg[0]["message"]
