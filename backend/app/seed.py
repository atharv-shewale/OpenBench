"""
OpenBench demo seed — fictional data only.

Personnel:
  1 admin, 2 owners, 2 managers, 8 regular users

Labs:
  L1  Vidyasagar Fab Lab   (Vidyasagar Engineering College, Kolkata)
  L2  Suryodaya Tech Lab   (Suryodaya Polytechnic, Pune)

Equipment (10):
  E1  UTM (Universal Testing Machine)         L1  testing      30 cr/hr
  E2  Brinell Hardness Tester                 L1  testing      15 cr/hr
  E3  CMM (Coordinate Measuring Machine)      L1  testing      25 cr/hr
  E4  3D Printer Alpha (Creality Ender 5+)    L1  fabrication  10 cr/hr
  E5  Laser Cutter Pro (80W CO2)              L1  fabrication  20 cr/hr
  E6  Workshop Lathe (Kirloskar)              L1  fabrication  18 cr/hr
  E7  Seminar Room A (30-seat)                L1  space         5 cr/hr
  E8  PCB Router Delta                        L2  fabrication  20 cr/hr
  E9  Tensile Tester Pro                      L2  testing      30 cr/hr
  E10 Oscilloscope Bench (4-ch, 200 MHz)      L2  testing       8 cr/hr

Sample completed journey (end-to-end):
  Arjun Kapoor books Oscilloscope Bench (E10) for 2 hours.
  → PENDING → APPROVED (Ramesh) → IN_PROGRESS (check-in) → COMPLETED (check-out)
  → 16 credits deducted, audit chain written for every step.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.clock import app_now
from app.models import (
    AuditLog, Badge, Booking, ConditionReport, CreditTransaction,
    Equipment, EquipmentAvailabilityWindow, Lab, LabMembership,
    Notification, User, UserCredential,
)
from app.services.auth_service import hash_password
from app.services.audit_service import write_audit
from app.services.credit_service import welcome_grant, hold_credits, deduct_credits

logger = logging.getLogger(__name__)


def _clear_all(db: Session) -> None:
    """Delete all rows in reverse dependency order."""
    for model in [
        AuditLog, Badge, ConditionReport, Notification, CreditTransaction,
        Booking, EquipmentAvailabilityWindow, Equipment,
        LabMembership, Lab, UserCredential, User,
    ]:
        db.query(model).delete()
    db.flush()


def _make_user(
    db: Session,
    email: str,
    full_name: str,
    password: str,
    role: str,
    organisation: str,
    credits: int = 0,
) -> User:
    u = User(
        email=email,
        full_name=full_name,
        hashed_password=hash_password(password),
        role=role,
        organisation=organisation,
        credit_balance=credits,
    )
    db.add(u)
    db.flush()
    return u


def _add_windows(db: Session, equip_id: int, windows: list[dict]) -> None:
    for w in windows:
        db.add(EquipmentAvailabilityWindow(equipment_id=equip_id, **w))


# Weekdays Mon-Fri 9-17
WEEKDAY_WINDOWS = [
    {"day_of_week": d, "start_time": "09:00", "end_time": "17:00"} for d in range(5)
]
# Mon-Sat 8-18
EXTENDED_WINDOWS = [
    {"day_of_week": d, "start_time": "08:00", "end_time": "18:00"} for d in range(6)
]


def run_seed(db: Session, wipe: bool = False) -> Dict[str, Any]:
    if wipe:
        _clear_all(db)

    now = app_now()

    # ── Users ──────────────────────────────────────────────────────────────────
    admin = _make_user(db, "platform.admin@openbench.in", "Platform Admin", "Admin@123", "admin", "OpenBench")

    # Owners
    anita = _make_user(db, "dr.anita.desai@vidyasagar.ac.in", "Dr. Anita Desai", "Owner@123", "owner", "Vidyasagar Engineering College")
    suresh = _make_user(db, "prof.suresh.iyer@suryodaya.edu.in", "Prof. Suresh Iyer", "Owner@123", "owner", "Suryodaya Polytechnic")

    # Managers
    priya = _make_user(db, "priya.sharma@vidyasagar.ac.in", "Priya Sharma", "Mgr@1234", "manager", "Vidyasagar Engineering College")
    ramesh = _make_user(db, "ramesh.nair@suryodaya.edu.in", "Ramesh Nair", "Mgr@1234", "manager", "Suryodaya Polytechnic")

    # Regular users
    rahul = _make_user(db, "rahul.mondal@iti-jadavpur.ac.in", "Rahul Mondal", "User@123", "user", "ITI Jadavpur", credits=50)
    sneha = _make_user(db, "sneha.patil@patilprecision.com", "Sneha Patil", "User@123", "user", "Patil Precision Parts (MSME)", credits=120)
    arjun = _make_user(db, "arjun.kapoor@kapoortech.in", "Arjun Kapoor", "User@123", "user", "KapoorTech Startup", credits=200)
    meena = _make_user(db, "meena.krishnan@iti-pune.ac.in", "Meena Krishnan", "User@123", "user", "ITI Pune", credits=80)
    vikram = _make_user(db, "vikram.shah@shahtools.in", "Vikram Shah", "User@123", "user", "Shah Tools (MSME)", credits=150)
    pooja = _make_user(db, "pooja.reddy@redtechlab.in", "Pooja Reddy", "User@123", "user", "RedTech Labs (Startup)", credits=90)
    kumar = _make_user(db, "kumar.das@dasengineering.in", "Kumar Das", "User@123", "user", "Das Engineering (MSME)", credits=60)
    farhan = _make_user(db, "farhan.sheikh@iti-kolkata.ac.in", "Farhan Sheikh", "User@123", "user", "ITI Kolkata", credits=40)

    # ── Labs ───────────────────────────────────────────────────────────────────
    lab1 = Lab(
        name="Vidyasagar Fab Lab",
        institution="Vidyasagar Engineering College",
        city="Kolkata",
        description=(
            "State-of-the-art fabrication and materials testing lab. "
            "Open to MSMEs, ITI students, and startups under the OpenBench initiative."
        ),
        contact_email="fablab@vidyasagar.ac.in",
    )
    lab2 = Lab(
        name="Suryodaya Tech Lab",
        institution="Suryodaya Polytechnic",
        city="Pune",
        description=(
            "Electronics and precision measurement lab with industry-grade PCB routing "
            "and mechanical testing equipment."
        ),
        contact_email="techlab@suryodaya.edu.in",
    )
    db.add_all([lab1, lab2])
    db.flush()

    # ── Lab memberships ────────────────────────────────────────────────────────
    db.add_all([
        LabMembership(user_id=anita.id, lab_id=lab1.id, role="owner"),
        LabMembership(user_id=priya.id, lab_id=lab1.id, role="manager"),
        LabMembership(user_id=suresh.id, lab_id=lab2.id, role="owner"),
        LabMembership(user_id=ramesh.id, lab_id=lab2.id, role="manager"),
    ])
    db.flush()

    # ── Equipment ──────────────────────────────────────────────────────────────
    e1 = Equipment(
        lab_id=lab1.id, name="UTM — Universal Testing Machine", type="testing",
        description="Tinius Olsen H25KS, 25 kN capacity. Tensile, compression & flexure tests.",
        credit_per_hour=30, max_booking_hours=3,
        rules={
            "max_sample_size_mm": "250 × 50 × 25",
            "pre_booking_checklist": "Upload material spec sheet before slot.",
            "operator_required": True,
        },
        required_credentials=["MATERIALS_TESTING_BASIC"],
    )
    e2 = Equipment(
        lab_id=lab1.id, name="Brinell Hardness Tester", type="testing",
        description="Laryee BH-3000B. HBW 1–650. Ferrous and non-ferrous metals.",
        credit_per_hour=15, max_booking_hours=2,
        rules={"max_specimen_weight_kg": 50, "indenter_type": "10mm carbide ball"},
    )
    e3 = Equipment(
        lab_id=lab1.id, name="CMM — Coordinate Measuring Machine", type="testing",
        description="Hexagon Global Silver 7.10.7. ±2.2 µm MPEe. Contact and scanning probe.",
        credit_per_hour=25, max_booking_hours=4,
        rules={
            "max_part_size_mm": "700 × 1000 × 700",
            "temperature_acclimatise_hours": 2,
            "probe_change_requires_staff": True,
        },
        required_credentials=["CMM_OPERATOR_BASIC"],
    )
    e4 = Equipment(
        lab_id=lab1.id, name="3D Printer Alpha (Creality Ender 5 Plus)", type="fabrication",
        description="Build volume 350×350×400 mm. PLA, PETG, TPU. 0.4 mm nozzle.",
        credit_per_hour=10, max_booking_hours=8,
        rules={
            "accepted_materials": ["PLA", "PETG", "TPU"],
            "file_format": "STL or 3MF",
            "slicer": "Creality Slicer or Cura",
            "bring_own_filament": False,
            "note": "Lab-provided PLA included. Exotic materials on request.",
        },
    )
    e5 = Equipment(
        lab_id=lab1.id, name="Laser Cutter Pro (80W CO2)", type="fabrication",
        description="Work area 600×900 mm. Cuts acrylic, MDF, wood, leather. Engraves metal.",
        credit_per_hour=20, max_booking_hours=4,
        rules={
            "prohibited_materials": ["PVC", "polycarbonate", "ABS"],
            "max_thickness_acrylic_mm": 12,
            "ventilation": "Always on during operation",
        },
        required_credentials=["LASER_SAFETY_L1"],
    )
    e6 = Equipment(
        lab_id=lab1.id, name="Workshop Lathe (Kirloskar Turn Master)", type="fabrication",
        description="Swing over bed 330 mm, centre distance 750 mm. Chuck dia 160 mm.",
        credit_per_hour=18, max_booking_hours=4,
        rules={
            "PPE_required": ["safety_glasses", "no_loose_clothing", "closed_toe_shoes"],
            "max_bar_dia_mm": 50,
        },
        required_credentials=["MACHINE_SHOP_SAFETY"],
    )
    e7 = Equipment(
        lab_id=lab1.id, name="Seminar Room A", type="space",
        description="30-seat A/C seminar room with projector, whiteboard, and video-conf setup.",
        credit_per_hour=5, max_booking_hours=8,
        rules={
            "max_occupancy": 30,
            "catering_allowed": False,
            "setup_buffer_minutes": 15,
        },
    )
    e8 = Equipment(
        lab_id=lab2.id, name="PCB Router Delta (LPKF ProtoMat S104)", type="fabrication",
        description="Mechanical PCB prototyping. Min track 100 µm. 4-layer boards.",
        credit_per_hour=20, max_booking_hours=4,
        rules={"file_format": "Gerber RS-274X", "max_board_size_mm": "229 × 305"},
    )
    e9 = Equipment(
        lab_id=lab2.id, name="Tensile Tester Pro (Mecmesin MultiTest 25-i)", type="testing",
        description="25 kN load cell. ISO 6892, ASTM E8 compliant.",
        credit_per_hour=30, max_booking_hours=3,
        rules={"gauge_length_mm": "50 or 80", "extensometer_available": True},
        required_credentials=["MATERIALS_TESTING_BASIC"],
    )
    e10 = Equipment(
        lab_id=lab2.id, name="Oscilloscope Bench (Rigol DS4054)", type="testing",
        description="4-channel, 500 MHz, 4 GSa/s. Function generator + power supply included.",
        credit_per_hour=8, max_booking_hours=4,
        rules={"max_input_voltage_v": 300, "probes_provided": True},
    )
    db.add_all([e1, e2, e3, e4, e5, e6, e7, e8, e9, e10])
    db.flush()

    # Availability windows
    for equip_id in [e1.id, e2.id, e3.id, e4.id, e5.id, e6.id, e7.id]:
        _add_windows(db, equip_id, WEEKDAY_WINDOWS)
    for equip_id in [e8.id, e9.id, e10.id]:
        _add_windows(db, equip_id, EXTENDED_WINDOWS)
    db.flush()

    # ── User credentials ───────────────────────────────────────────────────────
    db.add_all([
        UserCredential(
            user_id=arjun.id, credential_type="MACHINE_SHOP_SAFETY",
            issued_by="Vidyasagar Engineering College",
            issued_at=now - timedelta(days=90),
            expires_at=now + timedelta(days=275),
            is_verified=True, verified_by=priya.id,
        ),
        UserCredential(
            user_id=sneha.id, credential_type="MATERIALS_TESTING_BASIC",
            issued_by="CIPET Pune",
            issued_at=now - timedelta(days=60),
            expires_at=now + timedelta(days=305),
            is_verified=True, verified_by=ramesh.id,
        ),
        UserCredential(
            user_id=vikram.id, credential_type="LASER_SAFETY_L1",
            issued_by="Vidyasagar Engineering College",
            issued_at=now - timedelta(days=30),
            expires_at=now + timedelta(days=335),
            is_verified=True, verified_by=priya.id,
        ),
    ])
    db.flush()

    # ── Welcome credit audit entries ───────────────────────────────────────────
    # (credits were already added by _make_user directly; write audit entries)
    for u, amount in [
        (rahul, 50), (sneha, 120), (arjun, 200),
        (meena, 80), (vikram, 150), (pooja, 90), (kumar, 60), (farhan, 40),
    ]:
        db.add(CreditTransaction(
            user_id=u.id, tx_type="WELCOME_GRANT", amount=amount,
            balance_after=amount,
            description=f"Welcome grant for {u.full_name}",
        ))
    db.flush()

    # ── Sample completed journey ───────────────────────────────────────────────
    # Arjun Kapoor books Oscilloscope Bench (E10) for 2 hours — now - 3 days.
    slot_start = now - timedelta(days=3, hours=2)
    slot_end = slot_start + timedelta(hours=2)
    journey_cost = 16  # 2h × 8 cr/hr

    booking = Booking(
        user_id=arjun.id,
        equipment_id=e10.id,
        status="COMPLETED",
        slot_start=slot_start,
        slot_end=slot_end,
        checked_in_at=slot_start + timedelta(minutes=5),
        checked_out_at=slot_end - timedelta(minutes=3),
        credits_held=journey_cost,
        credits_charged=journey_cost,
        purpose="Testing signal integrity of prototype PCB for IoT sensor module.",
        manager_note="Approved — student ID verified.",
        decision_reason={
            "criterion": "Valid purpose, no conflicts, credentials not required for this equipment.",
            "automated": False,
            "notes": "Approved by Ramesh Nair.",
        },
    )
    db.add(booking)
    db.flush()

    # Deduct credits from Arjun's balance
    arjun.credit_balance -= journey_cost
    db.add(CreditTransaction(
        user_id=arjun.id,
        booking_id=booking.id,
        tx_type="DEDUCT",
        amount=-journey_cost,
        balance_after=arjun.credit_balance,
        description=f"Deducted for completed booking #{booking.id}",
    ))
    db.flush()

    # Post-session condition report
    db.add(ConditionReport(
        booking_id=booking.id,
        reporter_id=arjun.id,
        report_type="POST",
        condition="GOOD",
        notes="All probes returned, bench cleaned. No issues.",
    ))
    db.flush()

    # First-use badge
    db.add(Badge(
        user_id=arjun.id,
        badge_type="FIRST_BOOKING",
        awarded_at=slot_end,
        awarded_by=ramesh.id,
    ))
    db.flush()

    # Audit chain for the completed journey
    # Step 1: booking created
    write_audit(
        db, entity_type="booking", entity_id=booking.id, action="BOOKING_CREATED",
        payload={"user_id": arjun.id, "equipment_id": e10.id,
                 "slot_start": str(slot_start), "slot_end": str(slot_end),
                 "credits_held": journey_cost},
        actor_id=arjun.id, actor_role="user",
    )
    # Step 2: approved by Ramesh
    write_audit(
        db, entity_type="booking", entity_id=booking.id, action="BOOKING_APPROVED",
        payload={"manager_id": ramesh.id, "note": booking.manager_note,
                 "decision_reason": booking.decision_reason},
        actor_id=ramesh.id, actor_role="manager",
    )
    # Step 3: check-in
    write_audit(
        db, entity_type="booking", entity_id=booking.id, action="BOOKING_CHECKIN",
        payload={"checked_in_at": str(booking.checked_in_at)},
        actor_id=arjun.id, actor_role="user",
    )
    # Step 4: check-out + credit deduction
    write_audit(
        db, entity_type="booking", entity_id=booking.id, action="BOOKING_CHECKOUT",
        payload={"checked_out_at": str(booking.checked_out_at),
                 "credits_charged": journey_cost},
        actor_id=arjun.id, actor_role="user",
    )
    write_audit(
        db, entity_type="credit_tx", entity_id=booking.id, action="CREDIT_DEDUCTED",
        payload={"amount": journey_cost, "balance_after": arjun.credit_balance,
                 "booking_id": booking.id},
        actor_id=arjun.id, actor_role="user",
    )
    # Step 5: badge
    write_audit(
        db, entity_type="user", entity_id=arjun.id, action="BADGE_AWARDED",
        payload={"badge_type": "FIRST_BOOKING", "awarded_by": ramesh.id},
        actor_id=ramesh.id, actor_role="manager",
    )

    # ── A pending booking for demo interaction ─────────────────────────────────
    future_start = now + timedelta(hours=2)
    future_end = future_start + timedelta(hours=2)
    future_cost = 20  # 2h × 10 cr/hr (3D Printer)
    pending_booking = Booking(
        user_id=rahul.id,
        equipment_id=e4.id,
        status="PENDING",
        slot_start=future_start,
        slot_end=future_end,
        credits_held=future_cost,
        purpose="3D printing gear housing prototype for ITI final year project.",
    )
    db.add(pending_booking)
    db.flush()
    rahul.credit_held += future_cost

    write_audit(
        db, entity_type="booking", entity_id=pending_booking.id, action="BOOKING_CREATED",
        payload={"user_id": rahul.id, "equipment_id": e4.id,
                 "slot_start": str(future_start), "slot_end": str(future_end),
                 "credits_held": future_cost},
        actor_id=rahul.id, actor_role="user",
    )

    # An approved booking for Sneha on CMM
    approved_start = now + timedelta(hours=4)
    approved_end = approved_start + timedelta(hours=2)
    approved_cost = 50  # 2h × 25 cr/hr
    approved_booking = Booking(
        user_id=sneha.id,
        equipment_id=e3.id,
        status="APPROVED",
        slot_start=approved_start,
        slot_end=approved_end,
        credits_held=approved_cost,
        purpose="CMM inspection of batch components for automotive OEM delivery.",
        manager_note="Approved. Material spec sheet received.",
        decision_reason={"criterion": "Valid industrial purpose, credentials on file.", "automated": False},
    )
    db.add(approved_booking)
    db.flush()
    sneha.credit_held += approved_cost

    write_audit(
        db, entity_type="booking", entity_id=approved_booking.id, action="BOOKING_CREATED",
        payload={"user_id": sneha.id, "equipment_id": e3.id, "credits_held": approved_cost},
        actor_id=sneha.id, actor_role="user",
    )
    write_audit(
        db, entity_type="booking", entity_id=approved_booking.id, action="BOOKING_APPROVED",
        payload={"manager_id": priya.id, "note": approved_booking.manager_note},
        actor_id=priya.id, actor_role="manager",
    )

    db.commit()

    logger.info("Seed complete.")
    return {
        "message": "Demo data seeded successfully.",
        "users_created": 13,
        "labs_created": 2,
        "equipment_created": 10,
        "bookings_created": 3,
        "audit_entries": db.query(AuditLog).count(),
    }


if __name__ == "__main__":
    from app.database import SessionLocal, engine
    from app.database import Base
    import app.models  # noqa: ensure all tables are registered

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        result = run_seed(db, wipe=True)
        print(result)
    finally:
        db.close()

