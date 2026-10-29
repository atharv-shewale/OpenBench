"""
Tests for judge-proof gaps:
1. Ghost release triggers on clock advance and is idempotent (no duplicate releases or duplicate strike proposals).
2. Simulator Gini coefficient changes with the seed.
3. DEMO_MODE=false blocks demo endpoints with 403 Forbidden.
"""
from datetime import timedelta
import pytest

from app.clock import app_now, reset_clock
from app.models import ActionProposal, AuditLog, Booking, Equipment, Lab, User
from app.services.auth_service import hash_password, create_access_token
from tests.conftest import auth_headers


@pytest.fixture(autouse=True)
def clean_clock():
    reset_clock()
    yield
    reset_clock()


def test_ghost_release_triggers_on_clock_advance_and_is_idempotent(client, db):
    """
    (a) Ghost release triggers on clock advance and is idempotent:
    - Approved booking past the 20-min grace period without check-in/telemetry gets auto-released.
    - Exactly one pending strike proposal is created.
    - Subsequent clock advances do not duplicate release or create duplicate strike proposals.
    """
    manager = User(
        email="manager.kolhapur@panchganga-tech.ac.in",
        full_name="Priya Sharma",
        hashed_password=hash_password("Mgr@1234"),
        role="manager",
    )
    user = User(
        email="applicant@iti-shiroli.ac.in",
        full_name="Rahul ITI",
        hashed_password=hash_password("User@123"),
        role="user",
        credit_balance=100,
    )
    db.add_all([manager, user])
    db.flush()

    lab = Lab(name="Kolhapur Prototyping Lab", institution="Panchganga Institute", city="Kolhapur")
    db.add(lab)
    db.flush()

    equipment = Equipment(
        lab_id=lab.id,
        name="CNC 5-Axis Milling Machine",
        type="fabrication",
        credit_per_hour=30,
        deposit_credits=0,
        max_booking_hours=4,
        required_credentials=[],
        rules={},
    )
    db.add(equipment)
    db.flush()

    # Slot started 35 minutes ago, never checked in, no telemetry
    now = app_now()
    slot_start = now - timedelta(minutes=35)
    slot_end = slot_start + timedelta(hours=2)

    booking = Booking(
        user_id=user.id,
        equipment_id=equipment.id,
        status="APPROVED",
        priority_tier="COMMERCIAL",
        purpose="Production prototype validation",
        slot_start=slot_start,
        slot_end=slot_end,
        credits_held=60,
    )
    db.add(booking)
    db.commit()
    db.refresh(booking)

    manager_token = create_access_token(manager.id, "manager")

    # First clock advance: advance 1 minute
    advance_res = client.post(
        "/api/admin/clock/advance",
        json={"seconds": 60},
        headers=auth_headers(manager_token),
    )
    assert advance_res.status_code == 200

    # Verify booking is auto-released
    db.refresh(booking)
    assert booking.status == "AUTO_RELEASED"

    # Verify strike proposal created
    proposals = db.query(ActionProposal).filter(
        ActionProposal.entity_type == "user",
        ActionProposal.entity_id == user.id,
        ActionProposal.proposal_type == "STRIKE_PROPOSAL",
    ).all()
    assert len(proposals) == 1
    assert proposals[0].status == "PENDING"
    assert proposals[0].proposed_payload.get("booking_id") == booking.id

    # Verify audit log for release
    release_audits = db.query(AuditLog).filter(
        AuditLog.entity_type == "booking",
        AuditLog.entity_id == booking.id,
        AuditLog.action == "BOOKING_AUTO_RELEASED",
    ).all()
    assert len(release_audits) == 1

    # Second clock advance: advance another 10 minutes to verify IDEMPOTENCY
    advance_res2 = client.post(
        "/api/admin/clock/advance",
        json={"seconds": 600},
        headers=auth_headers(manager_token),
    )
    assert advance_res2.status_code == 200

    # Ensure booking remains AUTO_RELEASED and NO duplicate proposal or duplicate audit is created
    db.refresh(booking)
    assert booking.status == "AUTO_RELEASED"

    proposals_after = db.query(ActionProposal).filter(
        ActionProposal.entity_type == "user",
        ActionProposal.entity_id == user.id,
        ActionProposal.proposal_type == "STRIKE_PROPOSAL",
    ).all()
    assert len(proposals_after) == 1  # Still exactly 1 proposal!

    release_audits_after = db.query(AuditLog).filter(
        AuditLog.entity_type == "booking",
        AuditLog.entity_id == booking.id,
        AuditLog.action == "BOOKING_AUTO_RELEASED",
    ).all()
    assert len(release_audits_after) == 1  # Still exactly 1 audit entry!


def test_simulator_gini_changes_with_seed(client):
    """
    (b) Simulator Gini changes with the seed:
    Replaying synthetic demand under different RNG seeds yields distinct Gini inequality metrics.
    """
    res1 = client.get("/api/fairness-simulator/run?seed=42&days=30")
    assert res1.status_code == 200
    data1 = res1.json()

    res2 = client.get("/api/fairness-simulator/run?seed=9999&days=30")
    assert res2.status_code == 200
    data2 = res2.json()

    gini1_fcfs = data1["fcfs_metrics"]["gini_coefficient"]
    gini2_fcfs = data2["fcfs_metrics"]["gini_coefficient"]
    gini1_ob = data1["openbench_metrics"]["gini_coefficient"]
    gini2_ob = data2["openbench_metrics"]["gini_coefficient"]

    # Assert Gini coefficients differ across different RNG seeds
    assert gini1_fcfs != gini2_fcfs
    assert gini1_ob != gini2_ob


def test_demo_mode_false_blocks_demo_endpoints(client, db, monkeypatch):
    """
    (c) DEMO_MODE=false returns 403 on demo endpoints:
    - /api/auth/demo-login/{role}
    - /api/admin/reset-demo
    - /api/admin/clock/advance
    """
    # Create an admin user for authenticated admin calls
    admin = User(
        email="platform.admin@openbench.in",
        full_name="Platform Admin",
        hashed_password=hash_password("Admin@123"),
        role="admin",
    )
    db.add(admin)
    db.commit()

    admin_token = create_access_token(admin.id, "admin")

    # Set DEMO_MODE=false
    monkeypatch.setenv("DEMO_MODE", "false")

    # 1. demo-login should return 403 Forbidden
    login_res = client.post("/api/auth/demo-login/admin")
    assert login_res.status_code == 403
    assert "DEMO_MODE is disabled" in login_res.json()["detail"]

    # 2. reset-demo should return 403 Forbidden
    reset_res = client.post("/api/admin/reset-demo", headers=auth_headers(admin_token))
    assert reset_res.status_code == 403
    assert "DEMO_MODE is disabled" in reset_res.json()["detail"]

    # 3. clock advance should return 403 Forbidden
    clock_res = client.post(
        "/api/admin/clock/advance",
        json={"seconds": 3600},
        headers=auth_headers(admin_token),
    )
    assert clock_res.status_code == 403
    assert "DEMO_MODE is disabled" in clock_res.json()["detail"]
