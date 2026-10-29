"""
Tests for the audit log hash chain.

Verifies:
1. Entries are written correctly.
2. The hash chain is valid after multiple writes.
3. Tampering with a row breaks the chain.
4. The /api/audit/verify endpoint returns chain_valid: true.
"""
import pytest
from sqlalchemy.orm import Session

from app.services.audit_service import verify_chain, write_audit
from app.models import AuditLog
from tests.conftest import create_user_via_api, get_token, auth_headers


# ── Unit tests — directly call audit_service ───────────────────────────────────

class TestAuditChain:
    def test_genesis_prev_hash(self, db: Session):
        """First entry should have prev_hash = 64 zeros."""
        entry = write_audit(
            db,
            entity_type="test",
            entity_id=1,
            action="TEST_ACTION",
            payload={"key": "value"},
        )
        db.commit()
        assert entry.prev_hash == "0" * 64

    def test_second_entry_links_to_first(self, db: Session):
        e1 = write_audit(db, entity_type="test", entity_id=1, action="FIRST", payload={})
        db.flush()
        e2 = write_audit(db, entity_type="test", entity_id=1, action="SECOND", payload={})
        db.commit()
        assert e2.prev_hash == e1.hash

    def test_chain_validates_after_multiple_writes(self, db: Session):
        for i in range(10):
            write_audit(
                db,
                entity_type="test",
                entity_id=i,
                action=f"ACTION_{i}",
                payload={"seq": i},
                actor_id=1,
                actor_role="user",
            )
        db.commit()
        result = verify_chain(db)
        assert result["chain_valid"] is True
        assert result["total_entries"] == 10

    def test_empty_chain_is_valid(self, db: Session):
        result = verify_chain(db)
        assert result["chain_valid"] is True
        assert result["total_entries"] == 0

    def test_tampered_payload_breaks_chain(self, db: Session):
        """Directly mutating a row's payload should invalidate the chain."""
        e1 = write_audit(db, entity_type="test", entity_id=1, action="FIRST", payload={"x": 1})
        db.flush()
        write_audit(db, entity_type="test", entity_id=1, action="SECOND", payload={"x": 2})
        db.commit()

        # Tamper: change the payload of the first row
        e1_row = db.query(AuditLog).filter(AuditLog.id == e1.id).first()
        e1_row.payload = {"x": 999}  # tampered!
        db.commit()

        result = verify_chain(db)
        assert result["chain_valid"] is False
        assert result["broken_at_id"] == e1.id

    def test_tampered_hash_breaks_chain(self, db: Session):
        """Directly mutating a row's hash should invalidate the chain."""
        e1 = write_audit(db, entity_type="test", entity_id=1, action="FIRST", payload={})
        db.flush()
        write_audit(db, entity_type="test", entity_id=1, action="SECOND", payload={})
        db.commit()

        e1_row = db.query(AuditLog).filter(AuditLog.id == e1.id).first()
        e1_row.hash = "a" * 64  # corrupt hash
        db.commit()

        result = verify_chain(db)
        assert result["chain_valid"] is False

    def test_rationale_stored(self, db: Session):
        """Rationale field should be persisted for scheduler/AI actions."""
        rationale = "Scheduler detected missed check-in after 15 minutes."
        entry = write_audit(
            db,
            entity_type="booking",
            entity_id=42,
            action="BOOKING_NO_SHOW_PROPOSED",
            payload={"booking_id": 42},
            rationale=rationale,
            actor_id=None,
            actor_role="system",
        )
        db.commit()
        fetched = db.query(AuditLog).filter(AuditLog.id == entry.id).first()
        assert fetched.rationale == rationale


# ── Integration tests — via API endpoint ──────────────────────────────────────

class TestAuditAPI:
    def _get_admin_token(self, client, db):
        """Create an admin user directly and get a token."""
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

    def test_verify_endpoint_clean_chain(self, client, db):
        token = self._get_admin_token(client, db)
        # Write a few audit entries
        for i in range(3):
            write_audit(db, entity_type="test", entity_id=i, action=f"A{i}", payload={})
        db.commit()

        resp = client.get("/api/audit/verify", headers=auth_headers(token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["chain_valid"] is True
        assert data["total_entries"] == 3

    def test_audit_query_pagination(self, client, db):
        token = self._get_admin_token(client, db)
        for i in range(5):
            write_audit(db, entity_type="booking", entity_id=i, action=f"A{i}", payload={})
        db.commit()

        resp = client.get(
            "/api/audit?entity_type=booking&page=1&page_size=3",
            headers=auth_headers(token),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 5
        assert len(data["items"]) == 3

    def test_audit_forbidden_for_user(self, client, db):
        create_user_via_api(client)
        token = get_token(client)
        resp = client.get("/api/audit", headers=auth_headers(token))
        assert resp.status_code == 403

