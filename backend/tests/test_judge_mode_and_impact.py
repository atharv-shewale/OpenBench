"""
Unit tests for Judge Mode (one-click role logins, demo data reset)
and Impact Dashboard metrics.
"""
import pytest
from app.models import Booking, Equipment, Lab, User
from app.services.auth_service import hash_password, create_access_token
from tests.conftest import auth_headers


def test_demo_login_endpoints(client, db):
    # Seed sample users for demo login
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
    user = User(
        email="rahul.mondal@iti-jadavpur.ac.in",
        full_name="Rahul Mondal",
        hashed_password=hash_password("User@123"),
        role="user",
    )
    db.add_all([admin, owner, user])
    db.commit()

    # Test admin quick login
    res_admin = client.post("/api/auth/demo-login/admin")
    assert res_admin.status_code == 200
    assert "access_token" in res_admin.json()

    # Test owner quick login
    res_owner = client.post("/api/auth/demo-login/owner")
    assert res_owner.status_code == 200

    # Test apprentice / user quick login
    res_user = client.post("/api/auth/demo-login/apprentice")
    assert res_user.status_code == 200


def test_impact_metrics_endpoint(client, db):
    res = client.get("/api/analytics/impact")
    assert res.status_code == 200
    data = res.json()

    assert "idle_hours_unlocked" in data
    assert "equipment_value_utilised_inr" in data
    assert "estimated_cost_saved_inr" in data
    assert data["is_estimate"] is True
    assert "disclaimer" in data
    assert data["idle_hours_unlocked"] > 0
    assert data["equipment_value_utilised_inr"] > 0
    assert data["estimated_cost_saved_inr"] > 0


def test_reset_demo_database_endpoint(client, db):
    admin = User(
        email="admin@openbench.in",
        full_name="Admin Evaluator",
        hashed_password=hash_password("Admin@123"),
        role="admin",
    )
    db.add(admin)
    db.commit()

    token = create_access_token(admin.id, admin.role)

    res = client.post("/api/admin/reset-demo", headers=auth_headers(token))
    assert res.status_code == 200
    data = res.json()
    assert "successfully reset" in data["message"].lower()

    # Verify that seed data was re-instated
    users = db.query(User).all()
    assert len(users) >= 10

