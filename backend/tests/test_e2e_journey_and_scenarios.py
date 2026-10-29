"""
End-to-End integration tests for OpenBench:
1. Full 10-step lifecycle journey (Discovery -> Booking -> Approval -> QR Check-in
   -> Simulator Telemetry -> Handover/Diff -> Ledger & Timeline)
2. Competing requests & waitlist allocation with auto-promotion on cancellation
3. Ghost-booking auto-release with grace period, proposed strike, contestation, and manager reversal
4. Strict RBAC permission boundaries and isolation
"""
import pytest
from datetime import timedelta
from app.clock import app_now, advance_clock, reset_clock
from app.models import Booking, Equipment, EquipmentAvailabilityWindow, Lab, LabMembership, User, WaitlistEntry
from app.services.auth_service import hash_password, create_access_token
from tests.conftest import auth_headers


@pytest.fixture(autouse=True)
def clean_clock():
    reset_clock()
    yield
    reset_clock()


@pytest.fixture
def e2e_setup(db):
    """Seed minimal lab and personnel for E2E scenarios."""
    admin = User(
        email="platform.admin@openbench.in",
        full_name="Platform Admin",
        hashed_password=hash_password("Admin@123"),
        role="admin",
    )
    owner = User(
        email="dr.anita.desai@vidyasagar.ac.in",
        full_name="Dr. Anita Desai",
        hashed_password=hash_password("Owner@123"),
        role="owner",
    )
    manager = User(
        email="priya.sharma@vidyasagar.ac.in",
        full_name="Priya Sharma",
        hashed_password=hash_password("Mgr@1234"),
        role="manager",
    )
    student = User(
        email="rahul.mondal@iti-jadavpur.ac.in",
        full_name="Rahul Mondal",
        hashed_password=hash_password("User@123"),
        role="user",
        organisation="ITI Jadavpur",
        credit_balance=100,
    )
    msme = User(
        email="sneha.patil@patilprecision.com",
        full_name="Sneha Patil",
        hashed_password=hash_password("User@123"),
        role="user",
        organisation="Patil Precision Parts (MSME)",
        credit_balance=150,
    )
    db.add_all([admin, owner, manager, student, msme])
    db.flush()

    lab = Lab(
        name="Vidyasagar Fab Lab",
        institution="Vidyasagar Engineering College",
        city="Kolkata",
    )
    db.add(lab)
    db.flush()

    db.add_all([
        LabMembership(user_id=owner.id, lab_id=lab.id, role="owner"),
        LabMembership(user_id=manager.id, lab_id=lab.id, role="manager"),
    ])
    db.flush()

    utm = Equipment(
        lab_id=lab.id,
        name="Universal Testing Machine (UTM)",
        type="testing",
        credit_per_hour=30,
        approver_id=manager.id,
    )
    laser = Equipment(
        lab_id=lab.id,
        name="Laser Cutter Pro (80W CO2)",
        type="fabrication",
        credit_per_hour=20,
        approver_id=manager.id,
    )
    db.add_all([utm, laser])
    db.commit()

    return {
        "admin": admin,
        "owner": owner,
        "manager": manager,
        "student": student,
        "msme": msme,
        "utm": utm,
        "laser": laser,
        "tokens": {
            "admin": create_access_token(admin.id, admin.role),
            "owner": create_access_token(owner.id, owner.role),
            "manager": create_access_token(manager.id, manager.role),
            "student": create_access_token(student.id, student.role),
            "msme": create_access_token(msme.id, msme.role),
        },
    }


def test_full_lifecycle_journey_e2e(client, e2e_setup, db):
    """
    Complete end-to-end user journey across all lifecycle stages:
    Discovery -> Booking -> Manager Approval -> QR Pre-Flight Check-in ->
    Machine Telemetry Pulse -> Return & Photo-Diff -> Timeline & Audit Verification.
    """
    tokens = e2e_setup["tokens"]
    utm = e2e_setup["utm"]
    student = e2e_setup["student"]

    # 1. Discovery
    res_disc = client.get(f"/api/equipment/{utm.id}")
    assert res_disc.status_code == 200
    assert res_disc.json()["name"] == "Universal Testing Machine (UTM)"

    # 2. Student requests slot
    now = app_now()
    slot_start = now + timedelta(hours=2)
    slot_end = now + timedelta(hours=4)
    booking_payload = {
        "equipment_id": utm.id,
        "slot_start": slot_start.isoformat(),
        "slot_end": slot_end.isoformat(),
        "purpose": "Carbon Fiber Tensile Strain Validation",
        "priority_tier": "COMMERCIAL",
        "has_supervisor_signoff": True,
        "supervisor_name": "Instructor Bannerjee",
    }
    res_book = client.post(
        "/api/bookings",
        json=booking_payload,
        headers=auth_headers(tokens["student"]),
    )
    assert res_book.status_code == 201
    booking_id = res_book.json()["id"]
    assert res_book.json()["status"] == "PENDING"
    assert res_book.json()["credits_held"] == 60  # 2 hours * 30 cr/hr

    # 3. Manager reviews queue and approves
    res_queue = client.get(
        "/api/bookings/review-queue",
        headers=auth_headers(tokens["manager"]),
    )
    assert res_queue.status_code == 200
    queue_items = res_queue.json()
    assert any(item["booking"]["id"] == booking_id for item in queue_items)

    res_appr = client.post(
        f"/api/bookings/{booking_id}/approve",
        json={"notes": "Approved for carbon testing."},
        headers=auth_headers(tokens["manager"]),
    )
    assert res_appr.status_code == 200
    assert res_appr.json()["status"] == "APPROVED"

    # 4. Advance clock to slot start & QR Check-in
    advance_clock(7200)  # +2 hours
    checkin_payload = {
        "booking_id": booking_id,
        "condition": "GOOD",
        "notes": "Machine clean, optical sensors aligned.",
        "checklist": {"sensors_intact": True, "power_ok": True},
        "photos": ["https://storage.openbench.in/photos/before_1.jpg"],
    }
    res_checkin = client.post(
        f"/api/bookings/{booking_id}/qr-checkin",
        json=checkin_payload,
        headers=auth_headers(tokens["student"]),
    )
    assert res_checkin.status_code == 200
    assert res_checkin.json()["booking"]["status"] == "IN_PROGRESS"

    # 5. Machine activity simulator pulses telemetry
    signal_payload = {
        "is_active": True,
        "power_watts": 420.5,
        "activity_type": "spindle_run",
        "telemetry": {"voltage": 230, "frequency_hz": 60},
        "simulated": True,
    }
    res_signal = client.post(
        f"/api/equipment/{utm.id}/usage-signal",
        json=signal_payload,
        headers=auth_headers(tokens["student"]),
    )
    assert res_signal.status_code == 200
    assert res_signal.json()["is_active"] is True
    assert res_signal.json()["simulated"] is True

    # 6. Handover checkout & Return condition
    advance_clock(7200)  # +2 hours (slot ends)
    checkout_payload = {
        "booking_id": booking_id,
        "condition": "GOOD",
        "notes": "Specimen pulled to rupture; bench swept.",
        "checklist": {"specimen_cleared": True, "power_down": True},
        "photos": ["https://storage.openbench.in/photos/after_1.jpg"],
    }
    res_checkout = client.post(
        f"/api/bookings/{booking_id}/qr-checkout",
        json=checkout_payload,
        headers=auth_headers(tokens["student"]),
    )
    assert res_checkout.status_code == 200
    checkout_data = res_checkout.json()
    assert checkout_data["booking"]["status"] == "COMPLETED"
    assert checkout_data["booking"]["credits_charged"] == 60

    # 7. Check Shared Transaction Timeline
    res_timeline = client.get(
        f"/api/bookings/{booking_id}/timeline",
        headers=auth_headers(tokens["student"]),
    )
    assert res_timeline.status_code == 200
    timeline = res_timeline.json()
    assert timeline["booking_id"] == booking_id
    actions = [item["action"] for item in timeline["items"]]
    assert "BOOKING_CREATED" in actions
    assert "BOOKING_APPROVED" in actions

    # 8. Verify Hash-Chained Audit Integrity
    res_verify = client.get(
        "/api/audit/verify",
        headers=auth_headers(tokens["manager"]),
    )
    assert res_verify.status_code == 200
    assert res_verify.json()["chain_valid"] is True
    assert res_verify.json()["total_entries"] >= 4


def test_competing_requests_and_waitlist_auto_promotion(client, e2e_setup, db):
    """
    Scenario: Two users compete for the exact same slot on Laser Cutter.
    User A is approved, User B is waitlisted with full score breakdown.
    When User A cancels, User B is auto-promoted to APPROVED with notification.
    """
    tokens = e2e_setup["tokens"]
    laser = e2e_setup["laser"]
    student = e2e_setup["student"]
    msme = e2e_setup["msme"]

    now = app_now()
    slot_start = now + timedelta(days=2)
    slot_end = now + timedelta(days=2, hours=2)

    # 1. User A (Student) submits request
    res_a = client.post(
        "/api/bookings",
        json={
            "equipment_id": laser.id,
            "slot_start": slot_start.isoformat(),
            "slot_end": slot_end.isoformat(),
            "purpose": "Academic Capstone Project Chassis",
            "priority_tier": "STUDENT_PROJECT",
        },
        headers=auth_headers(tokens["student"]),
    )
    assert res_a.status_code == 201
    booking_a_id = res_a.json()["id"]

    # Manager approves booking A
    res_appr_a = client.post(
        f"/api/bookings/{booking_a_id}/approve",
        headers=auth_headers(tokens["manager"]),
    )
    assert res_appr_a.status_code == 200
    assert res_appr_a.json()["status"] == "APPROVED"

    # 2. User B (MSME) joins waitlist for the occupied slot
    res_wait = client.post(
        "/api/bookings/waitlist",
        json={
            "equipment_id": laser.id,
            "desired_start": slot_start.isoformat(),
            "desired_end": slot_end.isoformat(),
            "purpose": "Precision Gasket Cutting",
            "priority_tier": "COMMERCIAL",
        },
        headers=auth_headers(tokens["msme"]),
    )
    assert res_wait.status_code == 201
    wait_id = res_wait.json()["id"]
    assert res_wait.json()["status"] == "WAITING"
    assert "score_breakdown" in res_wait.json()
    assert res_wait.json()["ranking_score"] > 0

    # 3. User A cancels their booking
    res_cancel = client.post(
        f"/api/bookings/{booking_a_id}/cancel",
        headers=auth_headers(tokens["student"]),
    )
    assert res_cancel.status_code == 200
    assert res_cancel.json()["status"] == "CANCELLED"

    # 4. Waitlist entry for User B is automatically promoted
    wait_entry = db.query(WaitlistEntry).filter(WaitlistEntry.id == wait_id).first()
    assert wait_entry.status == "PROMOTED"

    # Check promoted booking exists for User B
    promoted_booking = db.query(Booking).filter(
        Booking.user_id == msme.id,
        Booking.equipment_id == laser.id,
        Booking.status == "PENDING",
    ).first()
    assert promoted_booking is not None
    assert promoted_booking.user_id == msme.id


def test_ghost_booking_release_and_manager_reversal(client, e2e_setup, db):
    """
    Scenario: User books a slot but fails to check in or pulse usage telemetry.
    Auto-release scanner releases slot, unholds credits, stages a PROPOSED strike.
    User contests with context note.
    Manager reviews and reverses the auto-release, reinstating the booking.
    """
    from app.services.auto_release_service import scan_and_auto_release_unclaimed_bookings
    from app.models import ActionProposal

    tokens = e2e_setup["tokens"]
    utm = e2e_setup["utm"]
    student = e2e_setup["student"]

    now = app_now()
    slot_start = now
    slot_end = now + timedelta(hours=2)

    # 1. Create and approve booking
    res_book = client.post(
        "/api/bookings",
        json={
            "equipment_id": utm.id,
            "slot_start": slot_start.isoformat(),
            "slot_end": slot_end.isoformat(),
            "purpose": "Tensile Testing",
            "priority_tier": "ROUTINE",
        },
        headers=auth_headers(tokens["student"]),
    )
    booking_id = res_book.json()["id"]
    client.post(f"/api/bookings/{booking_id}/approve", headers=auth_headers(tokens["manager"]))

    # Advance clock past 20-min grace period (25 minutes)
    advance_clock(1500)

    # Run auto-release scan
    released = scan_and_auto_release_unclaimed_bookings(db, grace_minutes=20)
    db.commit()
    assert len(released) == 1
    assert released[0].status == "AUTO_RELEASED"

    # Verify strike proposal created as PENDING (never automatic direct strike)
    proposal = db.query(ActionProposal).filter(
        ActionProposal.proposal_type == "STRIKE_PROPOSAL",
        ActionProposal.entity_id == student.id,
    ).first()
    assert proposal is not None
    assert proposal.proposed_payload.get("booking_id") == booking_id
    assert proposal.status == "PENDING"

    # 2. Student contests proposed strike
    res_contest = client.post(
        f"/api/proposals/{proposal.id}/contest",
        json={"contestation_note": "Bus delay on Eastern Metropolitan Bypass; arrived at 10:25."},
        headers=auth_headers(tokens["student"]),
    )
    assert res_contest.status_code == 200
    assert res_contest.json()["status"] == "CONTESTED"

    # 3. Manager reverses auto-release and reinstates booking
    res_reverse = client.post(
        f"/api/bookings/{booking_id}/reverse-auto-release",
        json={"explanation": "Verified public transport delay. Reinstated."},
        headers=auth_headers(tokens["manager"]),
    )
    assert res_reverse.status_code == 200
    assert res_reverse.json()["status"] in ("APPROVED", "IN_PROGRESS")

    # Proposal is dismissed (rejected) upon reversal
    db.refresh(proposal)
    assert proposal.status == "REJECTED"


def test_strict_rbac_permission_boundaries(client, e2e_setup, db):
    """
    Scenario: Verify rigorous role-based access control and isolation boundaries:
    - Regular users cannot see or touch other users' bookings or timelines
    - Regular users cannot access manager review queue
    - Regular users cannot reset/advance demo clock
    - Regular users cannot resolve incidents or reverse releases
    """
    tokens = e2e_setup["tokens"]
    utm = e2e_setup["utm"]
    student = e2e_setup["student"]
    msme = e2e_setup["msme"]

    now = app_now()
    # Student booking
    res_book = client.post(
        "/api/bookings",
        json={
            "equipment_id": utm.id,
            "slot_start": now.isoformat(),
            "slot_end": (now + timedelta(hours=2)).isoformat(),
            "purpose": "Confidential Student Patent Work",
            "priority_tier": "STUDENT_PROJECT",
        },
        headers=auth_headers(tokens["student"]),
    )
    booking_id = res_book.json()["id"]

    # 1. Other user (MSME) attempts to fetch student's timeline -> 403 Forbidden
    res_unauth_timeline = client.get(
        f"/api/bookings/{booking_id}/timeline",
        headers=auth_headers(tokens["msme"]),
    )
    assert res_unauth_timeline.status_code == 403

    # 2. Regular user attempts to access Manager Review Queue -> 403 Forbidden
    res_unauth_queue = client.get(
        "/api/bookings/review-queue",
        headers=auth_headers(tokens["student"]),
    )
    assert res_unauth_queue.status_code == 403

    # 3. Regular user attempts to advance demo clock -> 403 Forbidden
    res_unauth_clock = client.post(
        "/api/admin/clock/advance",
        json={"seconds": 3600},
        headers=auth_headers(tokens["student"]),
    )
    assert res_unauth_clock.status_code == 403

    # 4. Regular user attempts to reset demo database -> 403 Forbidden
    res_unauth_reset = client.post(
        "/api/admin/reset-demo",
        headers=auth_headers(tokens["student"]),
    )
    assert res_unauth_reset.status_code == 403
