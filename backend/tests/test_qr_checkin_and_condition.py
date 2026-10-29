"""
Tests for QR-based check-in and return:
1. Confirm identity and booking window enforcement.
2. Before-condition checklist with photos and notes.
3. After-condition report with checklist and notes.
4. Side-by-side comparison with signed photo URLs.
5. Extensions and late return handling (proposed penalty only; human manager confirms).
6. Advisory photo-diff (Pillow) with highlighted regions and mandatory 'Advisory only — a human decides' label.
7. Cryptographic signed URL verification and expiration against app_now().
"""
from datetime import datetime, timedelta
import io
import pytest
from PIL import Image

from app.clock import app_now, advance_clock, reset_clock
from app.models import ActionProposal, Booking, ConditionReport, Equipment, EquipmentAvailabilityWindow, Lab, User
from app.services.auth_service import hash_password, create_access_token
from app.services.storage_service import generate_signed_url, verify_signed_url, save_photo_bytes
from app.services.photo_diff_service import compare_condition_photos
from tests.conftest import auth_headers


@pytest.fixture(autouse=True)
def clean_clock():
    reset_clock()
    yield
    reset_clock()


class TestQRCheckinAndConditionFlow:
    def _setup_entities(self, db):
        owner = User(
            email="owner.test@poly.edu", full_name="Lab Owner",
            hashed_password=hash_password("Owner@123"), role="owner"
        )
        db.add(owner)
        db.flush()

        lab = Lab(name="Precision Testing Facility", institution="IIT Demo", city="Kolkata")
        db.add(lab)
        db.flush()

        equip = Equipment(
            lab_id=lab.id,
            name="Universal Testing Machine (UTM)",
            type="testing",
            credit_per_hour=25,
            deposit_credits=0,
            max_booking_hours=6,
            required_credentials=[],
            rules={},
        )
        db.add(equip)
        db.flush()

        user1 = User(
            email="booker1@msme.org", full_name="Subhashish Roy",
            hashed_password=hash_password("User@123"), role="user",
            credit_balance=100,
        )
        user2 = User(
            email="impostor@msme.org", full_name="Impostor User",
            hashed_password=hash_password("User@123"), role="user",
            credit_balance=100,
        )
        db.add_all([user1, user2])
        db.commit()

        return owner, equip, user1, user2

    def test_signed_urls_generation_and_verification(self):
        filename = "test_cond_photo.jpg"
        signed_url = generate_signed_url(filename, expires_in_seconds=60)
        assert "/api/media/condition-photos/" in signed_url
        assert "sig=" in signed_url
        assert "exp=" in signed_url

        # Parse query params
        query_part = signed_url.split("?")[1]
        params = dict(param.split("=") for param in query_part.split("&"))
        sig = params["sig"]
        exp = int(params["exp"])

        # Verification succeeds immediately
        assert verify_signed_url(filename, sig, exp) is True

        # Tampered signature fails
        assert verify_signed_url(filename, sig + "bad", exp) is False

        # Fast forward time past expiration
        advance_clock(120)  # +2 minutes
        assert verify_signed_url(filename, sig, exp) is False

    def test_advisory_photo_diff_detects_changes_and_stamps_advisory_label(self):
        # Create two distinct test images using Pillow
        img1 = Image.new("RGB", (300, 300), color=(180, 180, 180))
        buf1 = io.BytesIO()
        img1.save(buf1, format="JPEG")
        pre_file = save_photo_bytes(buf1.getvalue(), prefix="pre_test")

        # Second image with a dark altered region
        img2 = img1.copy()
        for x in range(50, 180):
            for y in range(50, 180):
                img2.putpixel((x, y), (30, 30, 30))
        buf2 = io.BytesIO()
        img2.save(buf2, format="JPEG")
        post_file = save_photo_bytes(buf2.getvalue(), prefix="post_test")

        diff_res = compare_condition_photos(pre_file, post_file)

        assert diff_res["advisory_label"] == "Advisory only — a human decides"
        assert diff_res["change_percentage"] > 5.0
        assert diff_res["is_significant"] is True
        assert diff_res["diff_photo_filename"] is not None
        assert "diff_" in diff_res["diff_photo_filename"]

    def test_qr_checkin_window_and_identity_enforcement(self, client, db):
        owner, equip, user1, user2 = self._setup_entities(db)
        now = app_now()

        # Slot starts 2 hours in the future
        future_start = now + timedelta(hours=2)
        future_end = future_start + timedelta(hours=2)

        booking = Booking(
            user_id=user1.id,
            equipment_id=equip.id,
            status="APPROVED",
            slot_start=future_start,
            slot_end=future_end,
            credits_held=50,
        )
        db.add(booking)
        db.commit()

        token1 = create_access_token(user1.id, "user")
        token2 = create_access_token(user2.id, "user")

        # 1. Impostor user cannot check in
        resp = client.post(
            f"/api/bookings/{booking.id}/qr-checkin",
            json={"condition": "GOOD", "checklist": {"power": True}},
            headers=auth_headers(token2),
        )
        assert resp.status_code == 403

        # 2. Early check-in attempt (2 hours before slot) is rejected
        resp = client.post(
            f"/api/bookings/{booking.id}/qr-checkin",
            json={"condition": "GOOD", "checklist": {"power": True}},
            headers=auth_headers(token1),
        )
        assert resp.status_code == 409
        assert "Check-in window opens" in resp.json()["detail"]

        # 3. Advance clock into check-in window (slot_start - 10 min)
        advance_clock(7200 - 600)  # +1 hr 50 min
        resp = client.post(
            f"/api/bookings/{booking.id}/qr-checkin",
            json={
                "condition": "GOOD",
                "checklist": {"power_ok": True, "calibration_verified": True},
                "notes": "Machine clean, datum zero verified.",
                "photos": ["pre_sample_photo.jpg"],
            },
            headers=auth_headers(token1),
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["booking"]["status"] == "IN_PROGRESS"
        assert data["pre_report"]["condition"] == "GOOD"
        assert data["pre_report"]["checklist_json"]["power_ok"] is True

    def test_complete_qr_checkout_flow_with_side_by_side_and_late_detection(self, client, db):
        owner, equip, user1, user2 = self._setup_entities(db)
        now = app_now()

        # Create two sample photos
        img1 = Image.new("RGB", (200, 200), color=(200, 200, 200))
        b1 = io.BytesIO()
        img1.save(b1, format="JPEG")
        pre_fn = save_photo_bytes(b1.getvalue(), prefix="pre_session")

        img2 = Image.new("RGB", (200, 200), color=(200, 200, 200))
        b2 = io.BytesIO()
        img2.save(b2, format="JPEG")
        post_fn = save_photo_bytes(b2.getvalue(), prefix="post_session")

        slot_start = now - timedelta(hours=1)
        slot_end = now + timedelta(hours=1)

        booking = Booking(
            user_id=user1.id,
            equipment_id=equip.id,
            status="APPROVED",
            slot_start=slot_start,
            slot_end=slot_end,
            credits_held=50,
        )
        db.add(booking)
        db.commit()

        token1 = create_access_token(user1.id, "user")

        # 1. Pre-session check-in
        checkin_resp = client.post(
            f"/api/bookings/{booking.id}/qr-checkin",
            json={
                "condition": "GOOD",
                "checklist": {"workspace_clean": True, "cabling_intact": True},
                "notes": "Pre-flight checks passed.",
                "photos": [pre_fn],
            },
            headers=auth_headers(token1),
        )
        assert checkin_resp.status_code == 200
        assert checkin_resp.json()["booking"]["status"] == "IN_PROGRESS"

        # 2. Fast-forward clock past slot_end to trigger late return detection
        # slot_end is +1 hr from initial now, fast forward by +2.5 hrs
        advance_clock(9000)

        # 3. Post-session check-out / return
        checkout_resp = client.post(
            f"/api/bookings/{booking.id}/qr-checkout",
            json={
                "condition": "GOOD",
                "checklist": {"cleaned_up": True, "powered_off": True},
                "notes": "Finished tensile test series.",
                "photos": [post_fn],
            },
            headers=auth_headers(token1),
        )
        assert checkout_resp.status_code == 200
        chk_data = checkout_resp.json()
        assert chk_data["booking"]["status"] == "COMPLETED"
        assert chk_data["is_late"] is True
        assert chk_data["overdue_minutes"] > 0
        assert chk_data["diff_result"] is not None
        assert chk_data["diff_result"]["advisory_label"] == "Advisory only — a human decides"

        # 4. Verify late return proposal created for manager review (human-in-the-loop)
        proposal = (
            db.query(ActionProposal)
            .filter(
                ActionProposal.entity_id == booking.id,
                ActionProposal.proposal_type == "LATE_RETURN_PENALTY",
            )
            .first()
        )
        assert proposal is not None
        assert proposal.status == "PENDING"
        assert "overdue_minutes" in proposal.proposed_payload

        # 5. Fetch side-by-side comparison report
        comp_resp = client.get(
            f"/api/bookings/{booking.id}/condition-comparison",
            headers=auth_headers(token1),
        )
        assert comp_resp.status_code == 200
        comp_data = comp_resp.json()
        assert comp_data["pre_report"] is not None
        assert comp_data["post_report"] is not None
        assert len(comp_data["pre_report"]["signed_photo_urls"]) == 1
        assert "sig=" in comp_data["pre_report"]["signed_photo_urls"][0]
        assert comp_data["advisory_banner"] == "Advisory only — a human decides"

    def test_session_extension_and_conflict_check(self, client, db):
        owner, equip, user1, user2 = self._setup_entities(db)
        now = app_now()

        slot_start = now - timedelta(minutes=30)
        slot_end = now + timedelta(minutes=30)  # 1 hour booking

        b1 = Booking(
            user_id=user1.id,
            equipment_id=equip.id,
            status="IN_PROGRESS",
            slot_start=slot_start,
            slot_end=slot_end,
            credits_held=25,
        )
        db.add(b1)
        db.commit()

        token1 = create_access_token(user1.id, "user")

        # Extend session by 1 hour (+25 credits)
        ext_resp = client.post(
            f"/api/bookings/{b1.id}/extend",
            json={"extra_hours": 1},
            headers=auth_headers(token1),
        )
        assert ext_resp.status_code == 200
        ext_data = ext_resp.json()
        assert ext_data["credits_held"] == 50

        # Create a conflicting booking on the same equipment for the next slot
        conflict_start = b1.slot_end + timedelta(minutes=15)
        conflict_end = conflict_start + timedelta(hours=2)
        b2 = Booking(
            user_id=user2.id,
            equipment_id=equip.id,
            status="APPROVED",
            slot_start=conflict_start,
            slot_end=conflict_end,
            credits_held=50,
        )
        db.add(b2)
        db.commit()

        # Another 1-hour extension now overlaps with b2
        fail_ext = client.post(
            f"/api/bookings/{b1.id}/extend",
            json={"extra_hours": 1},
            headers=auth_headers(token1),
        )
        assert fail_ext.status_code == 409
        assert "overlaps" in fail_ext.json()["detail"].lower()

