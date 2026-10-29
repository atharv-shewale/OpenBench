"""Integration tests for booking creation with early rejection, conflict prevention, and counterfactuals."""
from datetime import datetime, timedelta
import pytest
from tests.conftest import auth_headers, create_user_via_api, get_token
from app.models import Booking, Equipment, EquipmentAvailabilityWindow, Lab, LabMembership, User
from app.services.auth_service import hash_password, create_access_token
from app.clock import app_now


class TestBookingRequestFlow:
    def _setup_scenario(self, db):
        # 1. Owner & Lab
        owner = User(
            email="owner@uni.ac.in", full_name="Lab Director",
            hashed_password=hash_password("Owner@123"), role="owner"
        )
        db.add(owner)
        db.flush()

        lab = Lab(name="Advanced Fab Lab", institution="State Poly", city="Pune")
        db.add(lab)
        db.flush()

        # Equipment: requires 20 cr/hr + 10 deposit; requires CNC_CERT; Mon-Fri 09:00 - 18:00
        equip = Equipment(
            lab_id=lab.id,
            name="CNC Vertical Machining Center",
            type="fabrication",
            credit_per_hour=20,
            deposit_credits=10,
            max_booking_hours=4,
            required_credentials=["CNC_CERT"],
            rules={"requires_supervisor": True},
        )
        db.add(equip)
        db.flush()

        for d in range(5):
            db.add(EquipmentAvailabilityWindow(
                equipment_id=equip.id, day_of_week=d, start_time="09:00", end_time="18:00"
            ))
        db.commit()

        # Regular user with 50 credits
        user = User(
            email="tech@startup.in", full_name="Tech Founder",
            hashed_password=hash_password("User@123"), role="user",
            credit_balance=50,
        )
        db.add(user)
        db.commit()

        token = create_access_token(user.id, "user")
        return user, equip, token

    def test_booking_rejected_early_with_counterfactuals_when_missing_credentials(self, client, db):
        user, equip, token = self._setup_scenario(db)
        
        # User lacks CNC_CERT and supervisor sign-off
        now = app_now()
        # Find next weekday 10:00
        days_ahead = (7 - now.weekday()) % 7 or 7
        next_mon_10am = datetime.combine((now + timedelta(days=days_ahead)).date(), datetime.min.time()) + timedelta(hours=10)

        payload = {
            "equipment_id": equip.id,
            "slot_start": next_mon_10am.isoformat(),
            "slot_end": (next_mon_10am + timedelta(hours=2)).isoformat(),
            "purpose": "Prototype milling for precision sensor bracket",
            "priority_tier": "STANDARD",
            "group_name": "SensorTech Project",
            "has_supervisor_signoff": False,
        }

        resp = client.post("/api/bookings", json=payload, headers=auth_headers(token))
        assert resp.status_code == 422, resp.text
        data = resp.json()["detail"]
        assert "counterfactuals" in data
        assert len(data["counterfactuals"]) > 0

        # Check for actionable suggestions
        cf_types = [c["type"] for c in data["counterfactuals"]]
        assert "credential" in cf_types
        assert "supervision" in cf_types

    def test_prevents_overlapping_approved_bookings(self, client, db):
        user, equip, token = self._setup_scenario(db)

        # Create an existing confirmed booking directly
        slot_start = datetime(2026, 11, 2, 10, 0, 0)
        slot_end = datetime(2026, 11, 2, 12, 0, 0)
        existing_booking = Booking(
            user_id=user.id,
            equipment_id=equip.id,
            status="APPROVED",
            slot_start=slot_start,
            slot_end=slot_end,
            credits_held=50,
        )
        db.add(existing_booking)
        db.commit()

        # Second user attempts overlapping slot (11:00 - 13:00)
        user2 = User(
            email="user2@startup.in", full_name="User Two",
            hashed_password=hash_password("User@123"), role="user",
            credit_balance=100,
        )
        db.add(user2)
        db.commit()
        token2 = create_access_token(user2.id, "user")

        overlap_payload = {
            "equipment_id": equip.id,
            "slot_start": (slot_start + timedelta(hours=1)).isoformat(), # 11:00
            "slot_end": (slot_end + timedelta(hours=1)).isoformat(),     # 13:00
            "purpose": "Overlapping attempt",
            "has_supervisor_signoff": True,
            "supervisor_name": "Dr. Rao",
        }

        resp = client.post("/api/bookings", json=overlap_payload, headers=auth_headers(token2))
        assert resp.status_code == 409
        detail = resp.json()["detail"]
        assert "conflicts" in detail["message"].lower() or "reserved" in str(detail).lower()
        # Should provide alternative slots in next 7 days
        alt_slots = [c for c in detail["counterfactuals"] if c["type"] == "alternative_slot"]
        assert len(alt_slots) > 0
        assert "Alternative slot open on" in alt_slots[0]["message"]

