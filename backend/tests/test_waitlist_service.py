"""Integration test for auto-promoting waitlist on cancellation."""
from datetime import datetime, timedelta
import pytest
from app.models import Booking, Equipment, EquipmentAvailabilityWindow, Lab, User, WaitlistEntry
from app.services.auth_service import hash_password
from app.services.waitlist_service import auto_promote_waitlist_on_cancellation, join_waitlist
from app.services.booking_service import cancel_booking
from app.clock import app_now


class TestWaitlistAutoPromotion:
    def test_cancellation_auto_promotes_top_waitlist_user(self, db):
        now = app_now()

        # Lab & Equipment
        owner = User(
            email="owner_promo@test.in", full_name="Promo Owner",
            hashed_password=hash_password("Pass@123"), role="owner"
        )
        db.add(owner)
        db.flush()

        lab = Lab(name="Poly Lab", institution="Polytech", city="Pune")
        db.add(lab)
        db.flush()

        equip = Equipment(
            lab_id=lab.id, name="3D SLS Printer", type="fabrication",
            credit_per_hour=15, deposit_credits=0, max_booking_hours=4
        )
        db.add(equip)
        db.flush()

        # Original Booking: User 1 booked tomorrow 10:00 - 12:00
        slot_start = now + timedelta(days=1, hours=2)
        slot_end = slot_start + timedelta(hours=2)

        user1 = User(
            email="u1@test.in", full_name="User One",
            hashed_password=hash_password("Pass@123"), role="user", credit_balance=50
        )
        user2 = User(
            email="u2@test.in", full_name="User Two (Research)",
            hashed_password=hash_password("Pass@123"), role="user", credit_balance=60
        )
        user3 = User(
            email="u3@test.in", full_name="User Three (Standard)",
            hashed_password=hash_password("Pass@123"), role="user", credit_balance=60
        )
        db.add_all([user1, user2, user3])
        db.commit()

        orig_booking = Booking(
            user_id=user1.id,
            equipment_id=equip.id,
            status="APPROVED",
            slot_start=slot_start,
            slot_end=slot_end,
            credits_held=30,
        )
        db.add(orig_booking)
        db.commit()

        # User 2 & User 3 join waitlist for this overlapping slot
        w2 = join_waitlist(
            db, user2, equip.id, slot_start, slot_end,
            purpose="Urgent sensor housing", priority_tier="RESEARCH"
        )
        w3 = join_waitlist(
            db, user3, equip.id, slot_start, slot_end,
            purpose="Routine print", priority_tier="STANDARD"
        )
        db.commit()

        # User 2 has RESEARCH (25 pts) vs User 3 STANDARD (5 pts) -> User 2 must win promotion
        assert w2.ranking_score > w3.ranking_score

        # Cancel User 1's booking
        cancel_booking(db, orig_booking.id, user1)
        db.commit()

        # Check waitlist status
        db.refresh(w2)
        db.refresh(w3)
        assert w2.status == "PROMOTED"
        assert w3.status == "WAITING"

        # Check newly created booking for User 2
        promoted = db.query(Booking).filter(
            Booking.user_id == user2.id,
            Booking.equipment_id == equip.id,
            Booking.status == "PENDING"
        ).first()

        assert promoted is not None
        assert promoted.credits_held == 30
        assert user2.credit_held == 30

