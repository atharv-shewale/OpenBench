"""
Unit tests for usage signals, machine simulator telemetry,
auto-release with grace periods, proposed strike governance,
contestation, manager reversal, and incident reporting.
"""
from datetime import datetime, timedelta
import pytest

from app.clock import app_now, advance_clock, reset_clock
from app.models import (
    ActionProposal, Booking, Equipment, EquipmentAvailabilityWindow,
    Incident, Lab, Strike, User, WaitlistEntry,
)
from app.services.auth_service import hash_password, create_access_token
from app.services.auto_release_service import (
    scan_and_auto_release_unclaimed_bookings,
    reverse_auto_release,
    contest_proposal,
)
from tests.conftest import auth_headers


@pytest.fixture(autouse=True)
def clean_clock():
    reset_clock()
    yield
    reset_clock()


class TestUsageSignalAndAutoReleaseFlow:
    def _setup_scenario(self, db):
        owner = User(
            email="prof.sharma@iit.ac.in", full_name="Prof. Sharma",
            hashed_password=hash_password("Owner@123"), role="owner"
        )
        manager = User(
            email="priya.manager@iit.ac.in", full_name="Priya Manager",
            hashed_password=hash_password("Manager@123"), role="manager"
        )
        user1 = User(
            email="student1@iti.ac.in", full_name="Rahul ITI",
            hashed_password=hash_password("User@123"), role="user",
            credit_balance=100,
        )
        user2 = User(
            email="waitlisted@msme.org", full_name="Ananya MSME",
            hashed_password=hash_password("User@123"), role="user",
            credit_balance=80,
        )
        db.add_all([owner, manager, user1, user2])
        db.flush()

        lab = Lab(name="Heavy Fabrication & Testing Lab", institution="IIT Demo", city="Mumbai")
        db.add(lab)
        db.flush()

        equip = Equipment(
            lab_id=lab.id,
            name="Industrial Lathe & Milling Center",
            type="fabrication",
            credit_per_hour=30,
            deposit_credits=0,
            max_booking_hours=4,
            required_credentials=[],
            rules={},
        )
        db.add(equip)
        db.commit()

        return owner, manager, user1, user2, equip

    def test_usage_signal_telemetry_endpoint(self, client, db):
        owner, manager, user1, user2, equip = self._setup_scenario(db)
        token1 = create_access_token(user1.id, "user")

        now = app_now()
        booking = Booking(
            user_id=user1.id,
            equipment_id=equip.id,
            status="IN_PROGRESS",
            slot_start=now - timedelta(minutes=10),
            slot_end=now + timedelta(hours=1),
            credits_held=30,
        )
        db.add(booking)
        db.commit()

        # Emit simulated usage telemetry
        resp = client.post(
            f"/api/equipment/{equip.id}/usage-signal",
            json={
                "is_active": True,
                "power_watts": 450.5,
                "activity_type": "spindle_run",
                "telemetry": {"rpm": 1800, "vibration_g": 0.04},
                "simulated": True,
            },
            headers=auth_headers(token1),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_active"] is True
        assert data["simulated"] is True
        assert data["active_booking_id"] == booking.id

        # Verify DB updated
        db.refresh(equip)
        db.refresh(booking)
        assert equip.last_usage_signal_at is not None
        assert booking.last_usage_signal_at is not None
        assert equip.current_telemetry["power_watts"] == 450.5

    def test_auto_release_releases_unclaimed_slot_and_promotes_waitlist(self, client, db):
        owner, manager, user1, user2, equip = self._setup_scenario(db)
        now = app_now()

        # Slot started 25 minutes ago; user1 never checked in and sent no usage signal
        slot_start = now - timedelta(minutes=25)
        slot_end = slot_start + timedelta(hours=2)

        booking = Booking(
            user_id=user1.id,
            equipment_id=equip.id,
            status="APPROVED",
            slot_start=slot_start,
            slot_end=slot_end,
            credits_held=60,
        )
        db.add(booking)
        user1.credit_held = 60
        db.flush()

        # user2 is waiting on waitlist for this equipment
        w_entry = WaitlistEntry(
            user_id=user2.id,
            equipment_id=equip.id,
            desired_start=slot_start,
            desired_end=slot_end,
            status="WAITING",
            ranking_score=85.0,
        )
        db.add(w_entry)
        db.commit()

        # Run auto-release scan with 20 minute grace period
        released = scan_and_auto_release_unclaimed_bookings(db, grace_minutes=20)
        assert len(released) == 1
        assert released[0].id == booking.id

        # Verify booking status
        db.refresh(booking)
        db.refresh(user1)
        assert booking.status == "AUTO_RELEASED"
        assert booking.credits_held == 0
        assert user1.credit_held == 0  # Hold released

        # Verify waitlist promoted
        db.refresh(w_entry)
        assert w_entry.status in ("PROMOTED", "NOTIFIED")

        # Verify Strike was ONLY PROPOSED (Human in the loop)
        proposal = (
            db.query(ActionProposal)
            .filter(
                ActionProposal.entity_type == "user",
                ActionProposal.entity_id == user1.id,
                ActionProposal.proposal_type == "STRIKE_PROPOSAL",
            )
            .first()
        )
        assert proposal is not None
        assert proposal.status == "PENDING"
        assert user1.strike_count == 0  # No strike applied automatically!

    def test_booking_with_active_usage_signal_is_not_auto_released(self, client, db):
        owner, manager, user1, user2, equip = self._setup_scenario(db)
        now = app_now()

        # Slot started 25 minutes ago, but machine sensor emitted heartbeat 5 mins ago
        slot_start = now - timedelta(minutes=25)
        slot_end = slot_start + timedelta(hours=2)

        booking = Booking(
            user_id=user1.id,
            equipment_id=equip.id,
            status="APPROVED",
            slot_start=slot_start,
            slot_end=slot_end,
            credits_held=60,
            last_usage_signal_at=now - timedelta(minutes=5),  # Signal active!
        )
        db.add(booking)
        db.commit()

        released = scan_and_auto_release_unclaimed_bookings(db, grace_minutes=20)
        assert len(released) == 0
        db.refresh(booking)
        assert booking.status == "APPROVED"  # Kept active due to usage telemetry!

    def test_user_can_contest_strike_proposal_and_manager_can_reverse_release(self, client, db):
        owner, manager, user1, user2, equip = self._setup_scenario(db)
        now = app_now()

        booking = Booking(
            user_id=user1.id,
            equipment_id=equip.id,
            status="AUTO_RELEASED",
            slot_start=now - timedelta(minutes=30),
            slot_end=now + timedelta(hours=1),
            credits_held=0,
        )
        db.add(booking)
        db.flush()

        proposal = ActionProposal(
            proposal_type="STRIKE_PROPOSAL",
            entity_type="user",
            entity_id=user1.id,
            triggered_by="scheduler",
            rationale="Missed session test",
            proposed_payload={"user_id": user1.id, "booking_id": booking.id},
            status="PENDING",
        )
        db.add(proposal)
        db.commit()

        token_user = create_access_token(user1.id, "user")
        token_mgr = create_access_token(manager.id, "manager")

        # 1. User contests the proposed strike with explanation
        contest_resp = client.post(
            f"/api/proposals/{proposal.id}/contest",
            json={"contestation_note": "Campus shuttle had a flat tire; arrived 25 min late."},
            headers=auth_headers(token_user),
        )
        assert contest_resp.status_code == 200
        p_data = contest_resp.json()
        assert p_data["status"] == "CONTESTED"
        assert "shuttle had a flat tire" in p_data["contestation_note"]

        # 2. Manager reviews and reverses the auto-release
        rev_resp = client.post(
            f"/api/bookings/{booking.id}/reverse-auto-release",
            json={"explanation": "Valid transport excuse verified with college security."},
            headers=auth_headers(token_mgr),
        )
        assert rev_resp.status_code == 200
        b_data = rev_resp.json()
        assert b_data["status"] in ("APPROVED", "IN_PROGRESS")

        # Verify strike proposal was dismissed on reversal
        db.refresh(proposal)
        assert proposal.status == "REJECTED"

    def test_incident_reporting_and_resolution(self, client, db):
        owner, manager, user1, user2, equip = self._setup_scenario(db)
        now = app_now()

        booking = Booking(
            user_id=user1.id,
            equipment_id=equip.id,
            status="COMPLETED",
            slot_start=now - timedelta(hours=2),
            slot_end=now,
            credits_held=30,
        )
        db.add(booking)
        db.commit()

        token_user = create_access_token(user1.id, "user")
        token_mgr = create_access_token(manager.id, "manager")

        # 1. Report an incident (e.g. slight coolant leak)
        inc_resp = client.post(
            "/api/incidents",
            json={
                "booking_id": booking.id,
                "incident_type": "DAMAGE",
                "severity": "LOW",
                "description": "Coolant valve gasket showed slow dripping after high RPM cut.",
                "evidence_json": ["valve_photo_signed_url.jpg"],
            },
            headers=auth_headers(token_user),
        )
        assert inc_resp.status_code == 201
        inc_data = inc_resp.json()
        inc_id = inc_data["id"]
        assert inc_data["incident_type"] == "DAMAGE"
        assert inc_data["status"] == "OPEN"

        # 2. List incidents
        list_resp = client.get("/api/incidents", headers=auth_headers(token_mgr))
        assert list_resp.status_code == 200
        assert len(list_resp.json()) >= 1

        # 3. Manager resolves the incident
        res_resp = client.post(
            f"/api/incidents/{inc_id}/resolve",
            json={"resolution": "Replaced O-ring seal; pressure tested to 4 bar. Nominal."},
            headers=auth_headers(token_mgr),
        )
        assert res_resp.status_code == 200
        assert res_resp.json()["status"] == "RESOLVED"
        assert "Replaced O-ring" in res_resp.json()["resolution"]

    def test_demo_clock_controls_for_judges_and_admins(self, client, db):
        owner, manager, user1, user2, equip = self._setup_scenario(db)
        token_mgr = create_access_token(manager.id, "manager")

        # 1. Get clock state
        clk_resp = client.get("/api/admin/clock", headers=auth_headers(token_mgr))
        assert clk_resp.status_code == 200
        initial_offset = clk_resp.json()["offset_seconds"]

        # 2. Advance 1 hour (+3600s)
        adv_resp = client.post(
            "/api/admin/clock/advance",
            json={"seconds": 3600},
            headers=auth_headers(token_mgr),
        )
        assert adv_resp.status_code == 200
        assert adv_resp.json()["offset_seconds"] == initial_offset + 3600

        # 3. Advance 1 day (+86400s)
        adv_day = client.post(
            "/api/admin/clock/advance",
            json={"seconds": 86400},
            headers=auth_headers(token_mgr),
        )
        assert adv_day.status_code == 200
        assert adv_day.json()["offset_seconds"] == initial_offset + 3600 + 86400

        # 4. Reset clock
        rst_resp = client.post("/api/admin/clock/reset", headers=auth_headers(token_mgr))
        assert rst_resp.status_code == 200
        assert rst_resp.json()["offset_seconds"] == 0
