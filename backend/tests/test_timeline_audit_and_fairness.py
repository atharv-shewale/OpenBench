"""
Tests for shared transaction timeline, audit integrity verification, CSV export,
and fairness simulator.
"""
import pytest
from datetime import timedelta
from app.clock import app_now
from app.models import Booking, Equipment, User, AuditLog
from app.services.auth_service import hash_password, create_access_token
from app.services.audit_service import write_audit, verify_chain
from app.services.fairness_simulator_service import run_fairness_simulation, calculate_gini
from tests.conftest import auth_headers


def test_gini_calculation():
    # Perfect equality
    assert calculate_gini([10.0, 10.0, 10.0, 10.0]) == 0.0
    # Extreme inequality
    assert calculate_gini([0.0, 0.0, 0.0, 100.0]) > 0.70
    # Empty
    assert calculate_gini([]) == 0.0


def test_fairness_simulator_deterministic_replay():
    res1 = run_fairness_simulation(seed=42, days=30)
    res2 = run_fairness_simulation(seed=42, days=30)

    # Must be deterministic given same seed
    assert res1["fcfs_metrics"]["gini_coefficient"] == res2["fcfs_metrics"]["gini_coefficient"]
    assert res1["openbench_metrics"]["gini_coefficient"] == res2["openbench_metrics"]["gini_coefficient"]

    # OpenBench policy should yield lower Gini (more equitable) than FCFS
    assert res1["openbench_metrics"]["gini_coefficient"] < res1["fcfs_metrics"]["gini_coefficient"]

    # Must be explicitly labelled as synthetic
    assert res1["is_synthetic"] is True
    assert "SYNTHETIC" in res1["notice"]

    # Utilisation should remain high (>60%)
    assert res1["openbench_metrics"]["utilisation_pct"] > 60.0


def test_audit_verify_and_csv_endpoints(client, db):
    admin = User(
        email="admin@openbench.org",
        full_name="System Admin",
        hashed_password=hash_password("Admin@123"),
        role="admin",
    )
    db.add(admin)
    db.commit()

    token = create_access_token(admin.id, admin.role)

    # Verify audit hash chain
    res = client.get("/api/audit/verify", headers=auth_headers(token))
    assert res.status_code == 200
    data = res.json()
    assert "chain_valid" in data
    assert data["chain_valid"] is True
    assert "total_entries" in data

    # Export audit ledger to CSV
    res_csv = client.get("/api/audit/export.csv", headers=auth_headers(token))
    assert res_csv.status_code == 200
    assert res_csv.headers["content-type"].startswith("text/csv")
    assert "attachment" in res_csv.headers["content-disposition"]
    text = res_csv.text
    assert "id,timestamp,entity_type,entity_id,action" in text


def test_shared_booking_timeline_and_csv(client, db):
    user = User(
        email="rahul.mondal@iti.ac.in",
        full_name="Rahul Mondal",
        hashed_password=hash_password("User@123"),
        role="user",
    )
    manager = User(
        email="priya.manager@lab.ac.in",
        full_name="Priya Manager",
        hashed_password=hash_password("Manager@123"),
        role="manager",
    )
    from app.models import Lab
    lab = Lab(
        name="Materials Testing Lab",
        institution="Jadavpur ITI",
        city="Kolkata",
    )
    db.add_all([user, manager, lab])
    db.flush()

    eq = Equipment(
        lab_id=lab.id,
        name="Universal Testing Machine (UTM)",
        type="testing",
        credit_per_hour=50,
    )
    db.add(eq)
    db.commit()

    user_token = create_access_token(user.id, user.role)
    manager_token = create_access_token(manager.id, manager.role)

    now = app_now()
    booking = Booking(
        user_id=user.id,
        equipment_id=eq.id,
        slot_start=now,
        slot_end=now + timedelta(hours=2),
        purpose="Carbon fiber tensile modulus analysis",
        status="APPROVED",
    )
    db.add(booking)
    db.flush()

    # Write audit log entries associated with this booking
    write_audit(
        db,
        entity_type="booking",
        entity_id=booking.id,
        action="BOOKING_REQUESTED",
        payload={"booking_id": booking.id, "slot_hours": 2},
        actor_id=user.id,
        actor_role="user",
        rationale="Request submitted by apprentice with safety credential.",
    )
    write_audit(
        db,
        entity_type="booking",
        entity_id=booking.id,
        action="BOOKING_APPROVED",
        payload={"booking_id": booking.id, "approved_by": manager.full_name},
        actor_id=manager.id,
        actor_role="manager",
        rationale="Approved within weekly hours allowance.",
    )
    db.commit()

    # 1. Booker fetches timeline
    res_user = client.get(
        f"/api/bookings/{booking.id}/timeline",
        headers=auth_headers(user_token),
    )
    assert res_user.status_code == 200
    timeline = res_user.json()
    assert timeline["booking_id"] == booking.id
    assert len(timeline["items"]) == 2
    assert timeline["items"][0]["action"] == "BOOKING_REQUESTED"
    assert timeline["items"][0]["actor_name"] == "Rahul Mondal"
    assert timeline["items"][0]["rationale"] == "Request submitted by apprentice with safety credential."
    assert timeline["items"][1]["action"] == "BOOKING_APPROVED"
    assert timeline["items"][1]["actor_name"] == "Priya Manager"
    assert timeline["items"][1]["prev_hash"] == timeline["items"][0]["hash"]

    # 2. Manager fetches timeline
    res_mgr = client.get(
        f"/api/bookings/{booking.id}/timeline",
        headers=auth_headers(manager_token),
    )
    assert res_mgr.status_code == 200

    # 3. Booking timeline CSV export
    res_csv = client.get(
        f"/api/bookings/{booking.id}/timeline/export.csv",
        headers=auth_headers(user_token),
    )
    assert res_csv.status_code == 200
    assert res_csv.headers["content-type"].startswith("text/csv")
    csv_text = res_csv.text
    assert "audit_id,timestamp,action,actor_name" in csv_text
    assert "BOOKING_REQUESTED" in csv_text
    assert "Rahul Mondal" in csv_text
    assert "BOOKING_APPROVED" in csv_text


def test_fairness_simulator_api_endpoint(client):
    res = client.get("/api/fairness-simulator/run?seed=42&days=30")
    assert res.status_code == 200
    data = res.json()
    assert data["is_synthetic"] is True
    assert data["seed"] == 42
    assert "fcfs_metrics" in data
    assert "openbench_metrics" in data
    assert "comparison_summary" in data
    assert data["openbench_metrics"]["gini_coefficient"] < data["fcfs_metrics"]["gini_coefficient"]
    assert "hours_per_user_buckets" in data["openbench_metrics"]
    assert "daily_utilisation" in data["openbench_metrics"]
