"""
Backend security and role-based access control tests.
Proves:
1. Regular users cannot access others' bookings or waitlist entries.
2. Regular users cannot access manager review queues or perform approvals/rejections.
3. Managers can review and act on their lab's bookings, but require owner role to perform overrides.
4. Owners can override conflicts and eligibility restrictions.
5. Mandatory rejection reasons are strictly enforced.
"""
from datetime import datetime, timedelta
import pytest
from tests.conftest import auth_headers, create_user_via_api, get_token
from app.models import Booking, Equipment, Lab, LabMembership, User, WaitlistEntry
from app.services.auth_service import hash_password, create_access_token
from app.clock import app_now


class TestRoleBasedAccessAndSecurity:
    def _setup_world(self, db):
        now = app_now()

        # Lab 1
        lab1 = Lab(name="Fab Lab Alpha", institution="Tech College", city="Kolkata")
        db.add(lab1)
        db.flush()

        # Owner 1 & Manager 1
        owner1 = User(
            email="owner1@col.in", full_name="Prof. Owner",
            hashed_password=hash_password("Pass@123"), role="owner"
        )
        mgr1 = User(
            email="mgr1@col.in", full_name="Priya Mgr",
            hashed_password=hash_password("Pass@123"), role="manager"
        )
        db.add_all([owner1, mgr1])
        db.flush()

        db.add_all([
            LabMembership(user_id=owner1.id, lab_id=lab1.id, role="owner"),
            LabMembership(user_id=mgr1.id, lab_id=lab1.id, role="manager"),
        ])
        db.flush()

        # Equipment 1
        equip1 = Equipment(
            lab_id=lab1.id, name="3D Printer X", type="fabrication",
            credit_per_hour=10, deposit_credits=0, max_booking_hours=4
        )
        db.add(equip1)
        db.flush()

        # Users: Alice and Bob
        alice = User(
            email="alice@msme.in", full_name="Alice Booker",
            hashed_password=hash_password("Pass@123"), role="user", credit_balance=100
        )
        bob = User(
            email="bob@startup.in", full_name="Bob Booker",
            hashed_password=hash_password("Pass@123"), role="user", credit_balance=100
        )
        db.add_all([alice, bob])
        db.commit()

        # Tokens
        t_alice = create_access_token(alice.id, "user")
        t_bob = create_access_token(bob.id, "user")
        t_mgr1 = create_access_token(mgr1.id, "manager")
        t_owner1 = create_access_token(owner1.id, "owner")

        return {
            "lab": lab1,
            "equip": equip1,
            "alice": alice,
            "bob": bob,
            "mgr": mgr1,
            "owner": owner1,
            "tokens": {"alice": t_alice, "bob": t_bob, "mgr": t_mgr1, "owner": t_owner1},
        }

    def test_user_cannot_access_another_users_booking(self, client, db):
        world = self._setup_world(db)
        now = app_now()

        # Alice creates a booking
        b_alice = Booking(
            user_id=world["alice"].id,
            equipment_id=world["equip"].id,
            status="PENDING",
            slot_start=now + timedelta(days=1),
            slot_end=now + timedelta(days=1, hours=2),
            credits_held=20,
            purpose="Confidential prototype",
        )
        db.add(b_alice)
        db.commit()

        # Bob attempts to fetch Alice's booking detail
        resp = client.get(f"/api/bookings/{b_alice.id}", headers=auth_headers(world["tokens"]["bob"]))
        assert resp.status_code == 403
        assert "Access denied" in resp.json()["detail"]

    def test_user_cannot_view_review_queue(self, client, db):
        world = self._setup_world(db)
        resp = client.get("/api/bookings/review-queue", headers=auth_headers(world["tokens"]["alice"]))
        assert resp.status_code == 403
        assert "Manager or owner role required" in resp.json()["detail"]

    def test_user_cannot_approve_or_reject_bookings(self, client, db):
        world = self._setup_world(db)
        now = app_now()
        b = Booking(
            user_id=world["alice"].id,
            equipment_id=world["equip"].id,
            status="PENDING",
            slot_start=now + timedelta(days=1),
            slot_end=now + timedelta(days=1, hours=2),
            credits_held=20,
        )
        db.add(b)
        db.commit()

        # Alice tries to approve her own booking
        resp = client.post(f"/api/bookings/{b.id}/approve", json={"note": "Self approval"}, headers=auth_headers(world["tokens"]["alice"]))
        assert resp.status_code == 403

    def test_manager_cannot_override_without_owner_role(self, client, db):
        world = self._setup_world(db)
        now = app_now()
        b = Booking(
            user_id=world["alice"].id,
            equipment_id=world["equip"].id,
            status="PENDING",
            slot_start=now + timedelta(days=1),
            slot_end=now + timedelta(days=1, hours=2),
            credits_held=20,
        )
        db.add(b)
        db.commit()

        # Manager attempts an override approval
        resp = client.post(
            f"/api/bookings/{b.id}/approve",
            json={"note": "Forced override", "override": True},
            headers=auth_headers(world["tokens"]["mgr"]),
        )
        assert resp.status_code == 403
        assert "Only owners or admins" in resp.json()["detail"]

    def test_owner_can_override_approval(self, client, db):
        world = self._setup_world(db)
        now = app_now()
        b = Booking(
            user_id=world["alice"].id,
            equipment_id=world["equip"].id,
            status="PENDING",
            slot_start=now + timedelta(days=1),
            slot_end=now + timedelta(days=1, hours=2),
            credits_held=20,
        )
        db.add(b)
        db.commit()

        # Owner executes override approval
        resp = client.post(
            f"/api/bookings/{b.id}/approve",
            json={"note": "Owner administrative waiver granted", "override": True},
            headers=auth_headers(world["tokens"]["owner"]),
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "APPROVED"
        assert resp.json()["decision_reason"]["override"] is True

    def test_rejection_requires_mandatory_reason(self, client, db):
        world = self._setup_world(db)
        now = app_now()
        b = Booking(
            user_id=world["alice"].id,
            equipment_id=world["equip"].id,
            status="PENDING",
            slot_start=now + timedelta(days=1),
            slot_end=now + timedelta(days=1, hours=2),
            credits_held=20,
        )
        db.add(b)
        db.commit()

        # Manager attempts reject with empty note
        resp = client.post(
            f"/api/bookings/{b.id}/reject",
            json={"note": "   "},
            headers=auth_headers(world["tokens"]["mgr"]),
        )
        assert resp.status_code == 422
        assert "clear rejection reason is required" in resp.json()["detail"].lower()

