"""
Tests for authentication: register, login, refresh, role enforcement.
"""
import pytest

from tests.conftest import auth_headers, create_user_via_api, get_token


class TestRegister:
    def test_register_success(self, client, db):
        resp = client.post("/api/auth/register", json={
            "email": "newuser@test.com",
            "full_name": "New User",
            "password": "Secure@123",
            "organisation": "Test Org",
        })
        assert resp.status_code == 201
        data = resp.json()
        assert data["email"] == "newuser@test.com"
        assert data["role"] == "user"
        # Welcome grant of 50 credits
        assert data["credit_balance"] == 50

    def test_register_duplicate_email(self, client, db):
        create_user_via_api(client)
        resp = client.post("/api/auth/register", json={
            "email": "test@example.com",
            "full_name": "Duplicate",
            "password": "Secure@123",
        })
        assert resp.status_code == 409

    def test_register_missing_fields(self, client, db):
        resp = client.post("/api/auth/register", json={"email": "bad@test.com"})
        assert resp.status_code == 422


class TestLogin:
    def test_login_success(self, client, db):
        create_user_via_api(client)
        resp = client.post("/api/auth/login", data={
            "username": "test@example.com",
            "password": "Test@1234",
        })
        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"

    def test_login_wrong_password(self, client, db):
        create_user_via_api(client)
        resp = client.post("/api/auth/login", data={
            "username": "test@example.com",
            "password": "WRONG",
        })
        assert resp.status_code == 401

    def test_login_nonexistent_user(self, client, db):
        resp = client.post("/api/auth/login", data={
            "username": "ghost@example.com",
            "password": "Any@1234",
        })
        assert resp.status_code == 401


class TestRefreshToken:
    def test_refresh_success(self, client, db):
        create_user_via_api(client)
        login_resp = client.post("/api/auth/login", data={
            "username": "test@example.com",
            "password": "Test@1234",
        })
        refresh_token = login_resp.json()["refresh_token"]
        resp = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
        assert resp.status_code == 200
        assert "access_token" in resp.json()

    def test_refresh_invalid_token(self, client, db):
        resp = client.post("/api/auth/refresh", json={"refresh_token": "not.a.token"})
        assert resp.status_code == 401


class TestMe:
    def test_me_returns_profile(self, client, db):
        create_user_via_api(client)
        token = get_token(client)
        resp = client.get("/api/auth/me", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["email"] == "test@example.com"
        assert data["role"] == "user"

    def test_me_unauthenticated(self, client, db):
        resp = client.get("/api/auth/me")
        assert resp.status_code == 401

    def test_me_invalid_token(self, client, db):
        resp = client.get("/api/auth/me", headers={"Authorization": "Bearer fake.token"})
        assert resp.status_code == 401


class TestRoleEnforcement:
    def _make_admin(self, db):
        from app.models import User
        from app.services.auth_service import hash_password, create_access_token
        admin = User(
            email="admin@test.com",
            full_name="Test Admin",
            hashed_password=hash_password("Admin@123"),
            role="admin",
        )
        db.add(admin)
        db.commit()
        db.refresh(admin)
        return create_access_token(admin.id, "admin")

    def test_admin_endpoint_blocked_for_user(self, client, db):
        create_user_via_api(client)
        token = get_token(client)
        resp = client.get("/api/admin/users", headers=auth_headers(token))
        assert resp.status_code == 403

    def test_admin_endpoint_accessible_for_admin(self, client, db):
        token = self._make_admin(db)
        resp = client.get("/api/admin/users", headers=auth_headers(token))
        assert resp.status_code == 200

    def test_clock_advance_blocked_for_user(self, client, db):
        create_user_via_api(client)
        token = get_token(client)
        resp = client.post("/api/admin/clock/advance",
                           json={"seconds": 3600},
                           headers=auth_headers(token))
        assert resp.status_code == 403

    def test_clock_advance_accessible_for_admin(self, client, db):
        token = self._make_admin(db)
        resp = client.post("/api/admin/clock/advance",
                           json={"seconds": 7200},
                           headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["offset_seconds"] >= 7200  # could have been advanced before in session

