"""Tests for equipment CRUD, filtering, QR code generation, and eligibility checks."""
import pytest
from tests.conftest import auth_headers, create_user_via_api, get_token
from app.models import Equipment, Lab, LabMembership, User, UserCredential
from app.services.auth_service import hash_password, create_access_token
from app.clock import app_now
from datetime import timedelta

class TestEquipmentFeatures:
    def _setup_owner_and_lab(self, db):
        owner = User(
            email="owner@test.com",
            full_name="Lab Owner",
            hashed_password=hash_password("Owner@123"),
            role="owner",
            credit_balance=100,
        )
        db.add(owner)
        db.flush()

        lab = Lab(
            name="Test Innovation Lab",
            institution="National Tech Institute",
            city="Bengaluru",
            description="Leading prototyping lab",
        )
        db.add(lab)
        db.flush()

        db.add(LabMembership(user_id=owner.id, lab_id=lab.id, role="owner"))
        db.commit()
        db.refresh(owner)
        db.refresh(lab)
        token = create_access_token(owner.id, "owner")
        return owner, lab, token

    def test_owner_can_create_and_update_resource(self, client, db):
        owner, lab, token = self._setup_owner_and_lab(db)
        
        # 1. Create Resource
        payload = {
            "lab_id": lab.id,
            "name": "Precision CNC Mill",
            "type": "fabrication",
            "description": "5-axis high speed milling center",
            "credit_per_hour": 35,
            "max_booking_hours": 6,
            "location": "Bay 3, Heavy Machinery Hall",
            "access_conditions": "Safety goggles and steel-toe boots mandatory",
            "deposit_credits": 15,
            "required_credentials": ["CNC_OPERATOR_ADVANCED"],
            "availability_windows": [
                {"day_of_week": 0, "start_time": "09:00", "end_time": "18:00"},
                {"day_of_week": 1, "start_time": "09:00", "end_time": "18:00"}
            ],
            "rules": {"coolant_check": "Before cycle start", "max_feed_rate": 2000}
        }
        create_resp = client.post("/api/equipment", json=payload, headers=auth_headers(token))
        assert create_resp.status_code == 201, create_resp.text
        data = create_resp.json()
        assert data["name"] == "Precision CNC Mill"
        assert data["deposit_credits"] == 15
        assert data["location"] == "Bay 3, Heavy Machinery Hall"
        equip_id = data["id"]

        # 2. Update Resource
        update_resp = client.patch(f"/api/equipment/{equip_id}", json={
            "credit_per_hour": 40,
            "deposit_credits": 20
        }, headers=auth_headers(token))
        assert update_resp.status_code == 200
        assert update_resp.json()["credit_per_hour"] == 40
        assert update_resp.json()["deposit_credits"] == 20

    def test_qr_code_endpoint(self, client, db):
        owner, lab, token = self._setup_owner_and_lab(db)
        equip = Equipment(
            lab_id=lab.id,
            name="Optical Microscope",
            type="testing",
            credit_per_hour=10,
        )
        db.add(equip)
        db.commit()
        db.refresh(equip)

        resp = client.get(f"/api/equipment/{equip.id}/qr")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert len(resp.content) > 100

    def test_eligibility_check_missing_credits_and_credentials(self, client, db):
        owner, lab, _ = self._setup_owner_and_lab(db)
        equip = Equipment(
            lab_id=lab.id,
            name="Advanced Laser Cutter",
            type="fabrication",
            credit_per_hour=30,
            deposit_credits=20, # requires 50 total spendable
            required_credentials=["LASER_SAFETY_L2"]
        )
        db.add(equip)
        db.commit()
        db.refresh(equip)

        # User with 20 credits, no credentials
        user_reg = create_user_via_api(client, email="student@iti.ac.in", full_name="Student Booker")
        user_token = get_token(client, email="student@iti.ac.in")

        resp = client.get(f"/api/equipment/{equip.id}/eligibility", headers=auth_headers(user_token))
        assert resp.status_code == 200
        data = resp.json()
        assert data["is_eligible"] is False
        assert any("Missing required certification: LASER_SAFETY_L2" in r for r in data["reasons"])
        
        # Now grant credentials to the user
        user = db.query(User).filter(User.id == user_reg["id"]).first()
        cred = UserCredential(
            user_id=user.id,
            credential_type="LASER_SAFETY_L2",
            issued_at=app_now() - timedelta(days=5),
            expires_at=app_now() + timedelta(days=180),
            is_verified=True
        )
        db.add(cred)
        # Also give enough credits (50 welcome + 50 more)
        user.credit_balance = 100
        db.commit()

        resp2 = client.get(f"/api/equipment/{equip.id}/eligibility", headers=auth_headers(user_token))
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert data2["is_eligible"] is True
        assert len(data2["reasons"]) == 0

