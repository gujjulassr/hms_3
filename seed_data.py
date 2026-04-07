"""
Seed data script — populates the database with sample data for testing and demo.
Run: python seed_data.py

Creates:
- 3 doctors (cardiology, orthopedics, general medicine)
- 10 patients with UHIDs
- 1 staff/admin user
- Sessions for today and tomorrow
- Sample appointments (booked, checked_in, completed, cancelled, no_show)
- Sample ratings
"""
import asyncio
import uuid
from datetime import date, time, timedelta, datetime
from passlib.context import CryptContext

from config.database import engine, AsyncSessionLocal
from models.base import Base
from models.user import User
from models.patient import Patient
from models.doctor import Doctor
from models.session import Session
from models.appointment import Appointment
from models.audit_log import AuditLog
from models.rating import Rating
from models.beneficiary import Beneficiary
from services.slot_utils import count_slots

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
DEFAULT_PASSWORD = pwd_context.hash("password123")


async def seed():
    # Create all tables
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    print("[SEED] Tables created.")

    async with AsyncSessionLocal() as db:
        # ── Users & Doctors ──────────────────────────────────────────────
        doctors_data = [
            {"name": "Dr. Rajesh Shah", "email": "rajesh.shah@hms.com", "spec": "Cardiology"},
            {"name": "Dr. Priya Patel", "email": "priya.patel@hms.com", "spec": "Orthopedics"},
            {"name": "Dr. Amit Kumar", "email": "amit.kumar@hms.com", "spec": "General Medicine"},
        ]

        doctor_objs = []
        for d in doctors_data:
            user = User(id=uuid.uuid4(), email=d["email"], password_hash=DEFAULT_PASSWORD,
                       full_name=d["name"], phone="+91-9876543210", role="doctor", is_active=True)
            db.add(user)
            await db.flush()
            doctor = Doctor(id=uuid.uuid4(), user_id=user.id, specialization=d["spec"],
                          max_patients_per_day=30)
            db.add(doctor)
            doctor_objs.append((doctor, user))
            print(f"[SEED] Doctor: {d['name']} ({d['email']}) — password: password123")

        # ── Patients ─────────────────────────────────────────────────────
        patients_data = [
            {"name": "Arjun Mehta", "email": "arjun@test.com", "gender": "Male", "blood": "A+", "phone": "+91-9000000001"},
            {"name": "Sneha Reddy", "email": "sneha@test.com", "gender": "Female", "blood": "B+", "phone": "+91-9000000002"},
            {"name": "Vikram Singh", "email": "vikram@test.com", "gender": "Male", "blood": "O+", "phone": "+91-9000000003"},
            {"name": "Ananya Gupta", "email": "ananya@test.com", "gender": "Female", "blood": "AB+", "phone": "+91-9000000004"},
            {"name": "Rohan Joshi", "email": "rohan@test.com", "gender": "Male", "blood": "B-", "phone": "+91-9000000005"},
            {"name": "Meera Nair", "email": "meera@test.com", "gender": "Female", "blood": "A-", "phone": "+91-9000000006"},
            {"name": "Karan Malhotra", "email": "karan@test.com", "gender": "Male", "blood": "O-", "phone": "+91-9000000007"},
            {"name": "Divya Sharma", "email": "divya@test.com", "gender": "Female", "blood": "AB-", "phone": "+91-9000000008"},
            {"name": "Siddharth Rao", "email": "siddharth@test.com", "gender": "Male", "blood": "A+", "phone": "+91-9000000009"},
            {"name": "Pooja Verma", "email": "pooja@test.com", "gender": "Female", "blood": "B+", "phone": "+91-9000000010"},
        ]

        patient_objs = []
        for i, p in enumerate(patients_data, 1):
            user = User(id=uuid.uuid4(), email=p["email"], password_hash=DEFAULT_PASSWORD,
                       full_name=p["name"], phone=p["phone"], role="patient", is_active=True)
            db.add(user)
            await db.flush()
            uhid = f"HMS-{date.today().year}-{str(i).zfill(5)}"
            patient = Patient(id=uuid.uuid4(), user_id=user.id, uhid=uhid,
                            gender=p["gender"], blood_group=p["blood"],
                            risk_score=(i * 5) % 30)  # Varying risk scores
            db.add(patient)
            patient_objs.append((patient, user))
            print(f"[SEED] Patient: {p['name']} ({uhid}, {p['email']}) — password: password123")

        # ── Staff / Admin ────────────────────────────────────────────────
        staff_user = User(id=uuid.uuid4(), email="admin@hms.com", password_hash=DEFAULT_PASSWORD,
                         full_name="Admin User", phone="+91-9111111111", role="admin", is_active=True)
        db.add(staff_user)
        print(f"[SEED] Admin: Admin User (admin@hms.com) — password: password123")

        nurse_user = User(id=uuid.uuid4(), email="nurse@hms.com", password_hash=DEFAULT_PASSWORD,
                         full_name="Nurse Lakshmi", phone="+91-9222222222", role="nurse", is_active=True)
        db.add(nurse_user)
        print(f"[SEED] Nurse: Nurse Lakshmi (nurse@hms.com) — password: password123")

        await db.flush()

        # ── Sessions (today + tomorrow for all doctors) ──────────────────
        today = date.today()
        tomorrow = today + timedelta(days=1)

        session_objs = []
        for doctor, doc_user in doctor_objs:
            for d in [today, tomorrow]:
                slots = count_slots(time(9, 0), time(17, 0), 15)
                sess = Session(
                    id=uuid.uuid4(), doctor_id=doctor.id,
                    session_date=d, start_time=time(9, 0), end_time=time(17, 0),
                    slot_duration_minutes=15, max_per_slot=2, total_slots=slots,
                    status="active" if d == today else "scheduled"
                )
                db.add(sess)
                session_objs.append((sess, doctor, doc_user))
                print(f"[SEED] Session: Dr. {doc_user.full_name} on {d} (09:00-17:00, {slots} slots, {'ACTIVE' if d == today else 'SCHEDULED'})")

        await db.flush()

        # ── Appointments for today's sessions ────────────────────────────
        today_sessions = [(s, d, u) for s, d, u in session_objs if s.session_date == today]
        statuses = ["booked", "checked_in", "completed", "completed", "cancelled", "no_show",
                    "booked", "checked_in", "completed", "booked"]
        now = datetime.now()

        for sess, doctor, doc_user in today_sessions:
            # Assign 3-4 patients per doctor
            start_idx = doctor_objs.index((doctor, doc_user)) * 3
            assigned = patient_objs[start_idx:start_idx + 4]
            if len(assigned) < 4 and patient_objs:
                assigned.append(patient_objs[-1])

            for j, (patient, pat_user) in enumerate(assigned):
                slot_num = j + 1
                slot_t = (datetime.combine(today, time(9, 0)) + timedelta(minutes=15 * j)).time()
                # Skip lunch slots
                if time(13, 0) <= slot_t < time(13, 30):
                    slot_t = time(13, 30)

                status = statuses[j % len(statuses)]
                appt = Appointment(
                    id=uuid.uuid4(), session_id=sess.id, patient_id=patient.id,
                    booked_by=pat_user.id, slot_number=slot_num, slot_position=1,
                    slot_time=slot_t, status=status, priority="NORMAL"
                )

                if status in ("checked_in", "in_progress"):
                    appt.checked_in_at = now - timedelta(minutes=30 - j * 5)
                if status == "in_progress":
                    appt.started_at = now - timedelta(minutes=10)
                if status == "completed":
                    appt.checked_in_at = now - timedelta(hours=2, minutes=j * 15)
                    appt.started_at = now - timedelta(hours=1, minutes=45 - j * 10)
                    appt.completed_at = now - timedelta(hours=1, minutes=30 - j * 10)

                db.add(appt)
                print(f"[SEED] Appointment: {pat_user.full_name} → Dr. {doc_user.full_name} at {slot_t} ({status})")

        # ── Emergency appointment ────────────────────────────────────────
        if today_sessions and len(patient_objs) > 5:
            emerg_sess = today_sessions[0][0]
            emerg_pat, emerg_user = patient_objs[5]
            emerg_appt = Appointment(
                id=uuid.uuid4(), session_id=emerg_sess.id,
                patient_id=emerg_pat.id, booked_by=emerg_user.id,
                slot_number=0, slot_position=1, slot_time=time(9, 0),
                status="checked_in", priority="CRITICAL",
                is_emergency=True, checked_in_at=now - timedelta(minutes=5)
            )
            db.add(emerg_appt)
            print(f"[SEED] Emergency: {emerg_user.full_name} → Dr. {today_sessions[0][2].full_name}")

        # ── Ratings ──────────────────────────────────────────────────────
        ratings_data = [
            (0, 0, 5, "Excellent doctor, very thorough"),
            (1, 0, 4, "Good experience overall"),
            (2, 1, 5, "Very professional"),
            (3, 1, 3, "Long wait time"),
            (4, 2, 4, "Helpful and kind"),
        ]
        for pat_idx, doc_idx, score, feedback in ratings_data:
            if pat_idx < len(patient_objs) and doc_idx < len(doctor_objs):
                rating = Rating(
                    id=uuid.uuid4(),
                    patient_id=patient_objs[pat_idx][0].id,
                    doctor_id=doctor_objs[doc_idx][0].id,
                    rating=score,
                    feedback=feedback
                )
                db.add(rating)

        # ── Beneficiaries ────────────────────────────────────────────────
        if patient_objs:
            ben = Beneficiary(
                id=uuid.uuid4(), patient_id=patient_objs[0][0].id,
                name="Priya Mehta", relationship="Spouse", phone="+91-9000000099"
            )
            db.add(ben)

        await db.commit()
        print("\n[SEED] Database seeded successfully!")
        print("=" * 60)
        print("Login credentials (all use password: password123):")
        print("-" * 60)
        print("Doctors:  rajesh.shah@hms.com, priya.patel@hms.com, amit.kumar@hms.com")
        print("Patients: arjun@test.com, sneha@test.com, vikram@test.com, etc.")
        print("Admin:    admin@hms.com")
        print("Nurse:    nurse@hms.com")
        print("=" * 60)


if __name__ == "__main__":
    asyncio.run(seed())
