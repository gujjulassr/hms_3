"""
Seed script for HMS 3 — populates the database with sample data.
Run: python seed.py
"""
import uuid
from datetime import date, time, datetime, timedelta
from passlib.context import CryptContext
from sqlalchemy import create_engine
from sqlalchemy.orm import Session as DBSession
from models.base import Base
from models.user import User
from models.patient import Patient
from models.doctor import Doctor
from models.session import Session
from models.appointment import Appointment
from models.audit_log import AuditLog

# Sync engine for seeding
DATABASE_URL = "postgresql://postgres:postgres@localhost:5432/hms_3"
engine = create_engine(DATABASE_URL, echo=False)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

PASSWORD_HASH = pwd_context.hash("password123")

def seed():
    # Create all tables
    Base.metadata.create_all(engine)

    with DBSession(engine) as db:
        # Check if already seeded
        if db.query(User).first():
            print("Database already has data. Skipping seed.")
            return

        # ── ADMIN ──
        admin_id = uuid.uuid4()
        admin = User(id=admin_id, email="admin@hms.com", password_hash=PASSWORD_HASH,
                     full_name="Admin User", phone="9000000000", role="admin")

        # ── DOCTORS ──
        doc1_user_id, doc1_id = uuid.uuid4(), uuid.uuid4()
        doc2_user_id, doc2_id = uuid.uuid4(), uuid.uuid4()
        doc3_user_id, doc3_id = uuid.uuid4(), uuid.uuid4()

        doc_users = [
            User(id=doc1_user_id, email="dr.sharma@hms.com", password_hash=PASSWORD_HASH,
                 full_name="Dr. Anita Sharma", phone="9100000001", role="doctor"),
            User(id=doc2_user_id, email="dr.patel@hms.com", password_hash=PASSWORD_HASH,
                 full_name="Dr. Rajesh Patel", phone="9100000002", role="doctor"),
            User(id=doc3_user_id, email="dr.khan@hms.com", password_hash=PASSWORD_HASH,
                 full_name="Dr. Farah Khan", phone="9100000003", role="doctor"),
        ]
        doctors = [
            Doctor(id=doc1_id, user_id=doc1_user_id, specialization="General Medicine", max_patients_per_day=30),
            Doctor(id=doc2_id, user_id=doc2_user_id, specialization="Cardiology", max_patients_per_day=20),
            Doctor(id=doc3_id, user_id=doc3_user_id, specialization="Pediatrics", max_patients_per_day=25),
        ]

        # ── NURSES / STAFF ──
        nurse_id = uuid.uuid4()
        staff_id = uuid.uuid4()
        staff_users = [
            User(id=nurse_id, email="nurse.priya@hms.com", password_hash=PASSWORD_HASH,
                 full_name="Priya Nair", phone="9200000001", role="nurse"),
            User(id=staff_id, email="staff.ravi@hms.com", password_hash=PASSWORD_HASH,
                 full_name="Ravi Kumar", phone="9200000002", role="staff"),
        ]

        # ── PATIENTS ──
        patients_data = [
            ("Amit Verma",    "amit@example.com",    "9300000001", "Male",   "B+",  date(1990, 5, 12), "123, MG Road, Mumbai",       "Sunita Verma",  "9300100001"),
            ("Sneha Iyer",    "sneha@example.com",   "9300000002", "Female", "O+",  date(1985, 8, 25), "45, Anna Nagar, Chennai",     "Raj Iyer",      "9300100002"),
            ("Rahul Singh",   "rahul@example.com",   "9300000003", "Male",   "A-",  date(1978, 1, 3),  "78, Sector 15, Noida",        "Meera Singh",   "9300100003"),
            ("Priya Reddy",   "priyar@example.com",  "9300000004", "Female", "AB+", date(1995, 11, 20),"9, Jubilee Hills, Hyderabad", "Kiran Reddy",   "9300100004"),
            ("Arjun Das",     "arjun@example.com",   "9300000005", "Male",   "O-",  date(2000, 3, 8),  "22, Salt Lake, Kolkata",      "Rupa Das",      "9300100005"),
            ("Meera Joshi",   "meera@example.com",   "9300000006", "Female", "A+",  date(1992, 7, 14), "56, Koregaon Park, Pune",     "Anil Joshi",    "9300100006"),
            ("Vikram Malhotra","vikram@example.com",  "9300000007", "Male",   "B-",  date(1988, 12, 1), "34, Connaught Place, Delhi",  "Neha Malhotra", "9300100007"),
            ("Ananya Pillai", "ananya@example.com",   "9300000008", "Female", "O+",  date(2002, 4, 19), "11, Marine Drive, Kochi",     "Suresh Pillai",  "9300100008"),
        ]

        patient_user_ids = []
        patient_ids = []
        patient_users = []
        patient_records = []

        for i, (name, email, phone, gender, bg, dob, addr, ec_name, ec_phone) in enumerate(patients_data, start=1):
            uid = uuid.uuid4()
            pid = uuid.uuid4()
            patient_user_ids.append(uid)
            patient_ids.append(pid)

            patient_users.append(
                User(id=uid, email=email, password_hash=PASSWORD_HASH,
                     full_name=name, phone=phone, role="patient")
            )
            patient_records.append(
                Patient(id=pid, user_id=uid, uhid=f"HMS-2026-{str(i).zfill(5)}",
                        gender=gender, blood_group=bg, date_of_birth=dob,
                        address=addr, emergency_contact_name=ec_name,
                        emergency_contact_phone=ec_phone, risk_score=0)
            )

        # ── SESSIONS (today + tomorrow for Dr. Sharma & Dr. Patel) ──
        today = date.today()
        tomorrow = today + timedelta(days=1)

        sess1_id = uuid.uuid4()  # Dr. Sharma today
        sess2_id = uuid.uuid4()  # Dr. Patel today
        sess3_id = uuid.uuid4()  # Dr. Sharma tomorrow
        sess4_id = uuid.uuid4()  # Dr. Khan tomorrow

        sessions = [
            Session(id=sess1_id, doctor_id=doc1_id, session_date=today,
                    start_time=time(9, 0), end_time=time(17, 0),
                    lunch_start=time(13, 0), lunch_end=time(13, 30),
                    slot_duration_minutes=15, max_per_slot=2, total_slots=30,
                    status="scheduled"),
            Session(id=sess2_id, doctor_id=doc2_id, session_date=today,
                    start_time=time(10, 0), end_time=time(16, 0),
                    lunch_start=time(13, 0), lunch_end=time(13, 30),
                    slot_duration_minutes=20, max_per_slot=2, total_slots=16,
                    status="scheduled"),
            Session(id=sess3_id, doctor_id=doc1_id, session_date=tomorrow,
                    start_time=time(9, 0), end_time=time(17, 0),
                    lunch_start=time(13, 0), lunch_end=time(13, 30),
                    slot_duration_minutes=15, max_per_slot=2, total_slots=30,
                    status="scheduled"),
            Session(id=sess4_id, doctor_id=doc3_id, session_date=tomorrow,
                    start_time=time(9, 0), end_time=time(14, 0),
                    lunch_start=time(13, 0), lunch_end=time(13, 30),
                    slot_duration_minutes=15, max_per_slot=2, total_slots=14,
                    status="scheduled"),
        ]

        # ── APPOINTMENTS (mix of statuses for today's sessions) ──
        appointments = [
            # Dr. Sharma today — 4 appointments
            Appointment(id=uuid.uuid4(), session_id=sess1_id, patient_id=patient_ids[0],
                        booked_by=patient_user_ids[0], slot_number=1, slot_position=1,
                        slot_time=time(9, 0), status="booked", priority="NORMAL"),
            Appointment(id=uuid.uuid4(), session_id=sess1_id, patient_id=patient_ids[1],
                        booked_by=patient_user_ids[1], slot_number=2, slot_position=1,
                        slot_time=time(9, 15), status="booked", priority="NORMAL"),
            Appointment(id=uuid.uuid4(), session_id=sess1_id, patient_id=patient_ids[2],
                        booked_by=patient_user_ids[2], slot_number=3, slot_position=1,
                        slot_time=time(9, 30), status="booked", priority="HIGH",
                        notes="Follow-up for chest pain"),
            Appointment(id=uuid.uuid4(), session_id=sess1_id, patient_id=patient_ids[3],
                        booked_by=staff_id, slot_number=4, slot_position=1,
                        slot_time=time(9, 45), status="booked", priority="NORMAL",
                        notes="Booked by front desk"),

            # Dr. Patel today — 3 appointments
            Appointment(id=uuid.uuid4(), session_id=sess2_id, patient_id=patient_ids[4],
                        booked_by=patient_user_ids[4], slot_number=1, slot_position=1,
                        slot_time=time(10, 0), status="booked", priority="NORMAL"),
            Appointment(id=uuid.uuid4(), session_id=sess2_id, patient_id=patient_ids[5],
                        booked_by=patient_user_ids[5], slot_number=2, slot_position=1,
                        slot_time=time(10, 20), status="booked", priority="HIGH",
                        notes="Referred by Dr. Sharma"),
            Appointment(id=uuid.uuid4(), session_id=sess2_id, patient_id=patient_ids[6],
                        booked_by=patient_user_ids[6], slot_number=3, slot_position=1,
                        slot_time=time(10, 40), status="booked", priority="NORMAL"),

            # Dr. Sharma tomorrow — 2 appointments
            Appointment(id=uuid.uuid4(), session_id=sess3_id, patient_id=patient_ids[7],
                        booked_by=patient_user_ids[7], slot_number=1, slot_position=1,
                        slot_time=time(9, 0), status="booked", priority="NORMAL"),
            Appointment(id=uuid.uuid4(), session_id=sess3_id, patient_id=patient_ids[0],
                        booked_by=patient_user_ids[0], slot_number=5, slot_position=1,
                        slot_time=time(10, 0), status="booked", priority="NORMAL",
                        notes="Return visit"),

            # Dr. Khan tomorrow — 1 appointment
            Appointment(id=uuid.uuid4(), session_id=sess4_id, patient_id=patient_ids[3],
                        booked_by=patient_user_ids[3], slot_number=1, slot_position=1,
                        slot_time=time(9, 0), status="booked", priority="NORMAL"),
        ]

        # ── AUDIT LOGS ──
        audit_logs = [
            AuditLog(id=uuid.uuid4(), user_id=admin_id, action="SEED_DATABASE",
                     target_type="system", details={"note": "Initial sample data loaded"}),
        ]

        # ── INSERT IN ORDER (respect foreign keys) ──
        # 1. All users first
        db.add(admin)
        db.add_all(doc_users)
        db.add_all(staff_users)
        db.add_all(patient_users)
        db.flush()

        # 2. Doctors & patients (depend on users)
        db.add_all(doctors)
        db.add_all(patient_records)
        db.flush()

        # 3. Sessions (depend on doctors)
        db.add_all(sessions)
        db.flush()

        # 4. Appointments & audit logs
        db.add_all(appointments)
        db.add_all(audit_logs)
        db.commit()

        print("Seed complete!")
        print(f"  - 1 admin")
        print(f"  - 3 doctors (Dr. Sharma, Dr. Patel, Dr. Khan)")
        print(f"  - 1 nurse, 1 staff")
        print(f"  - 8 patients (HMS-2026-00001 to HMS-2026-00008)")
        print(f"  - 4 sessions (2 today, 2 tomorrow)")
        print(f"  - 10 appointments")
        print(f"\nAll passwords: password123")
        print(f"\nLogin emails:")
        print(f"  Admin:    admin@hms.com")
        print(f"  Doctors:  dr.sharma@hms.com, dr.patel@hms.com, dr.khan@hms.com")
        print(f"  Nurse:    nurse.priya@hms.com")
        print(f"  Staff:    staff.ravi@hms.com")
        print(f"  Patients: amit@example.com, sneha@example.com, rahul@example.com, etc.")


if __name__ == "__main__":
    seed()
