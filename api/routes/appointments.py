"""
Standalone REST API routes for appointments.
Section 4 requirement: GET /available-slots, POST /book-appointment, GET /appointments
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from datetime import datetime, date, time, timedelta
import uuid as uuid_lib

from config.database import AsyncSessionLocal as async_session
from config.auth import get_current_user
from models.session import Session
from models.appointment import Appointment
from models.patient import Patient
from models.doctor import Doctor
from models.user import User
from models.beneficiary import Beneficiary
from services.slot_utils import generate_slot_times, is_lunch_time
from services.audit import log_action

router = APIRouter(prefix="/api", tags=["appointments"])


# ─── GET /my-profile ───────────────────────────────────────────────────────

@router.get("/my-profile")
async def my_profile(user: dict = Depends(get_current_user)):
    """Get current logged-in patient's profile."""
    async with async_session() as db:
        result = await db.execute(
            select(Patient, User).join(User, Patient.user_id == User.id)
            .where(User.email == user["email"])
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="Patient profile not found.")
        patient, usr = row
        return {
            "uhid": patient.uhid,
            "name": usr.full_name,
            "email": usr.email,
            "phone": usr.phone or "",
            "gender": patient.gender or "",
            "blood_group": patient.blood_group or "",
            "date_of_birth": str(patient.date_of_birth) if patient.date_of_birth else "",
            "address": patient.address or "",
            "emergency_contact_name": patient.emergency_contact_name or "",
            "emergency_contact_phone": patient.emergency_contact_phone or "",
        }


# ─── PUT /my-profile ──────────────────────────────────────────────────────

class UpdateProfileRequest(BaseModel):
    full_name: str = ""
    phone: str = ""
    gender: str = ""
    blood_group: str = ""
    date_of_birth: str = ""
    address: str = ""
    emergency_contact_name: str = ""
    emergency_contact_phone: str = ""


@router.put("/my-profile")
async def update_my_profile(req: UpdateProfileRequest, user: dict = Depends(get_current_user)):
    """Update logged-in patient's profile."""
    async with async_session() as db:
        result = await db.execute(
            select(Patient, User).join(User, Patient.user_id == User.id)
            .where(User.email == user["email"])
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="Patient profile not found.")
        patient, usr = row

        if req.full_name:
            usr.full_name = req.full_name
        if req.phone:
            usr.phone = req.phone
        if req.gender:
            patient.gender = req.gender
        if req.blood_group:
            patient.blood_group = req.blood_group
        if req.date_of_birth:
            try:
                patient.date_of_birth = datetime.strptime(req.date_of_birth, "%Y-%m-%d").date()
            except ValueError:
                pass
        if req.address:
            patient.address = req.address
        if req.emergency_contact_name:
            patient.emergency_contact_name = req.emergency_contact_name
        if req.emergency_contact_phone:
            patient.emergency_contact_phone = req.emergency_contact_phone

        await log_action(db, usr.id, "UPDATE_PROFILE", "patient", patient.id, {"uhid": patient.uhid})
        await db.commit()
    return {"message": "Profile updated."}


# ─── GET /my-appointments ─────────────────────────────────────────────────

@router.get("/my-reports")
async def my_reports(user: dict = Depends(get_current_user)):
    """Get consultation reports for logged-in patient."""
    from models.report import ConsultationReport
    async with async_session() as db:
        pat_r = await db.execute(
            select(Patient).join(User, Patient.user_id == User.id)
            .where(User.email == user["email"])
        )
        patient = pat_r.scalars().first()
        if not patient:
            return {"reports": []}

        result = await db.execute(
            select(ConsultationReport, Doctor, User)
            .join(Doctor, ConsultationReport.doctor_id == Doctor.id)
            .join(User, Doctor.user_id == User.id)
            .where(ConsultationReport.patient_id == patient.id)
            .order_by(ConsultationReport.created_at.desc())
        )
        rows = result.all()
        reports = []
        for report, doctor, doc_user in rows:
            reports.append({
                "id": str(report.id),
                "doctor": doc_user.full_name,
                "specialization": doctor.specialization or "",
                "content": report.content,
                "doctor_notes": report.doctor_notes or "",
                "drive_link": report.drive_link or "",
                "created_at": str(report.created_at) if report.created_at else "",
            })
    return {"reports": reports}


@router.get("/my-appointments")
async def my_appointments(user: dict = Depends(get_current_user)):
    """Get appointments for logged-in patient AND their beneficiaries."""
    async with async_session() as db:
        # Find patient by email
        pat_r = await db.execute(
            select(Patient).join(User, Patient.user_id == User.id)
            .where(User.email == user["email"])
        )
        patient = pat_r.scalars().first()
        if not patient:
            return {"appointments": []}

        # Get own patient ID + all beneficiary patient IDs
        patient_ids = [patient.id]

        ben_r = await db.execute(select(Beneficiary).where(Beneficiary.patient_id == patient.id))
        bens = ben_r.scalars().all()
        for b in bens:
            # Find beneficiary's patient record by name
            bp_r = await db.execute(
                select(Patient).join(User, Patient.user_id == User.id)
                .where(User.full_name.ilike(f"%{b.name}%"))
            )
            bp = bp_r.scalars().first()
            if bp:
                patient_ids.append(bp.id)

        # Fetch appointments for self + beneficiaries
        result = await db.execute(
            select(Appointment, Session, Doctor, Patient)
            .join(Session, Appointment.session_id == Session.id)
            .join(Doctor, Session.doctor_id == Doctor.id)
            .join(Patient, Appointment.patient_id == Patient.id)
            .where(Appointment.patient_id.in_(patient_ids))
            .order_by(Session.session_date.desc(), Appointment.slot_time)
        )
        rows = result.all()
        appointments = []
        for appt, session, doctor, appt_patient in rows:
            # Get doctor name
            doc_user_r = await db.execute(select(User).where(User.id == doctor.user_id))
            doc_user = doc_user_r.scalars().first()
            # Get patient name
            pat_user_r = await db.execute(select(User).where(User.id == appt_patient.user_id))
            pat_user = pat_user_r.scalars().first()

            is_self = appt_patient.id == patient.id
            appointments.append({
                "patient_name": pat_user.full_name if pat_user else "Unknown",
                "patient_uhid": appt_patient.uhid,
                "is_self": is_self,
                "doctor": doc_user.full_name if doc_user else "Unknown",
                "specialization": doctor.specialization or "",
                "date": str(session.session_date),
                "time": str(appt.slot_time),
                "status": appt.status,
                "priority": appt.priority,
            })
        return {"appointments": appointments}


# ─── GET /doctors ──────────────────────────────────────────────────────────

@router.get("/doctors")
async def list_doctors(
    specialization: str = Query("", description="Filter by specialization"),
    user: dict = Depends(get_current_user)
):
    """List all doctors, optionally filtered by specialization."""
    async with async_session() as db:
        stmt = select(Doctor, User).join(User, Doctor.user_id == User.id)
        if specialization:
            stmt = stmt.where(Doctor.specialization.ilike(f"%{specialization}%"))
        result = await db.execute(stmt)
        rows = result.all()

        doctors = []
        for doctor, doc_user in rows:
            # Check if doctor has any upcoming sessions
            sess_r = await db.execute(
                select(func.count(Session.id)).where(
                    Session.doctor_id == doctor.id,
                    Session.session_date >= date.today(),
                    Session.status.in_(["scheduled", "active"])
                )
            )
            session_count = sess_r.scalar() or 0
            doctors.append({
                "name": doc_user.full_name,
                "specialization": doctor.specialization or "",
                "max_patients_per_day": doctor.max_patients_per_day,
                "upcoming_sessions": session_count,
            })
    return {"doctors": doctors}


# ─── POST /cancel-my-appointment ──────────────────────────────────────────

class CancelRequest(BaseModel):
    doctor_name: str


@router.post("/cancel-my-appointment")
async def cancel_my_appointment(req: CancelRequest, user: dict = Depends(get_current_user)):
    """Cancel logged-in patient's appointment with a doctor."""
    async with async_session() as db:
        pat_r = await db.execute(
            select(Patient).join(User, Patient.user_id == User.id)
            .where(User.email == user["email"])
        )
        patient = pat_r.scalars().first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found.")

        result = await db.execute(
            select(Appointment, Session, Doctor, User)
            .join(Session, Appointment.session_id == Session.id)
            .join(Doctor, Session.doctor_id == Doctor.id)
            .join(User, Doctor.user_id == User.id)
            .where(
                Appointment.patient_id == patient.id,
                User.full_name.ilike(f"%{req.doctor_name}%"),
                Appointment.status.in_(["booked", "checked_in"]),
                Session.session_date >= date.today()
            )
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail="No active appointment found with this doctor.")

        appt, session, doctor, doc_user = row
        appt.status = "cancelled"
        patient.risk_score = (patient.risk_score or 0) + 10
        await log_action(db, patient.user_id, "CANCEL", "appointment", appt.id,
                         {"uhid": patient.uhid, "doctor": doc_user.full_name})
        await db.commit()

    return {"message": f"Appointment with Dr. {doc_user.full_name} on {session.session_date} at {appt.slot_time} cancelled."}


# ─── POST /reschedule-appointment ─────────────────────────────────────────

class RescheduleRequest(BaseModel):
    doctor_name: str
    new_date: str = ""
    new_time: str = ""


@router.post("/reschedule-appointment")
async def reschedule_appointment(req: RescheduleRequest, user: dict = Depends(get_current_user)):
    """Reschedule a patient's appointment — cancels old (no risk penalty) and books new slot."""
    from tools.appointment_tools import find_free_slot

    async with async_session() as db:
        # Find patient
        pat_r = await db.execute(
            select(Patient).join(User, Patient.user_id == User.id)
            .where(User.email == user["email"])
        )
        patient = pat_r.scalars().first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found.")

        # Find existing appointment
        appt_r = await db.execute(
            select(Appointment, Session, Doctor, User)
            .join(Session, Appointment.session_id == Session.id)
            .join(Doctor, Session.doctor_id == Doctor.id)
            .join(User, Doctor.user_id == User.id)
            .where(
                Appointment.patient_id == patient.id,
                User.full_name.ilike(f"%{req.doctor_name}%"),
                Appointment.status.in_(["booked", "checked_in"]),
                Session.session_date >= date.today()
            )
        )
        old_row = appt_r.first()
        if not old_row:
            raise HTTPException(status_code=404, detail="No active appointment found to reschedule.")

        old_appt, old_session, doctor, doc_user = old_row

        # Find new session/slot
        new_date = date.today()
        if req.new_date:
            try:
                new_date = datetime.strptime(req.new_date, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

        # Find session on new date
        sess_r = await db.execute(
            select(Session).where(
                Session.doctor_id == doctor.id,
                Session.session_date == new_date,
                Session.status.in_(["scheduled", "active"])
            )
        )
        new_session = sess_r.scalars().first()
        if not new_session:
            raise HTTPException(status_code=404, detail=f"No session for Dr. {doc_user.full_name} on {new_date}.")

        # Check if specific requested slot is available
        if req.new_time:
            requested_time = datetime.strptime(req.new_time, "%H:%M").time()
            all_slots = generate_slot_times(
                new_session.start_time, new_session.end_time, new_session.slot_duration_minutes,
                new_session.lunch_start, new_session.lunch_end, new_session.overtime_minutes
            )
            target_slot = next((s for s in all_slots if s["slot_time"] == requested_time), None)
            if target_slot:
                booked_count = await db.execute(
                    select(func.count(Appointment.id)).where(
                        Appointment.session_id == new_session.id,
                        Appointment.slot_number == target_slot["slot_number"],
                        Appointment.status.in_(["booked", "checked_in", "in_progress"])
                    )
                )
                count = booked_count.scalar() or 0
                if count >= new_session.max_per_slot:
                    raise HTTPException(status_code=409, detail=f"Slot at {req.new_time} is full on {new_date}.")

        # Find free slot
        result = await find_free_slot(db, new_session, req.new_time)
        if not result:
            raise HTTPException(status_code=409, detail=f"No available slots on {new_date}.")

        slot_number, position, slot_time = result

        # Check not same slot as old
        if new_session.id == old_session.id and slot_number == old_appt.slot_number:
            raise HTTPException(status_code=400, detail="New slot is the same as current appointment.")

        # Cancel old appointment (NO risk penalty — it's a reschedule)
        old_appt.status = "rescheduled"
        await log_action(db, patient.user_id, "RESCHEDULE", "appointment", old_appt.id,
                         {"uhid": patient.uhid, "doctor": doc_user.full_name,
                          "old_date": str(old_session.session_date), "old_time": str(old_appt.slot_time),
                          "new_date": str(new_date), "new_time": str(slot_time)})

        # Book new appointment
        new_appt = Appointment(
            id=uuid_lib.uuid4(),
            session_id=new_session.id,
            patient_id=patient.id,
            booked_by=patient.user_id,
            slot_number=slot_number,
            slot_position=position,
            slot_time=slot_time,
            status="booked"
        )
        db.add(new_appt)

        # Get patient user for email
        pat_user_r = await db.execute(select(User).where(User.id == patient.user_id))
        pat_user = pat_user_r.scalars().first()
        await db.commit()

    # Send reschedule email with calendar invite
    if pat_user:
        from services.notifications.service import notify_reschedule
        await notify_reschedule(pat_user.email, pat_user.full_name, doc_user.full_name,
                                str(old_session.session_date), str(old_appt.slot_time),
                                str(new_date), str(slot_time), patient.uhid)

    return {
        "message": f"Rescheduled: {old_session.session_date} {old_appt.slot_time} → {new_date} {slot_time} with Dr. {doc_user.full_name}",
        "old": {"date": str(old_session.session_date), "time": str(old_appt.slot_time)},
        "new": {"date": str(new_date), "time": str(slot_time)},
    }


# ─── Beneficiaries CRUD ──────────────────────────────────────────────────

@router.get("/my-beneficiaries")
async def get_beneficiaries(user: dict = Depends(get_current_user)):
    """Get logged-in patient's beneficiaries."""
    async with async_session() as db:
        pat_r = await db.execute(
            select(Patient).join(User, Patient.user_id == User.id)
            .where(User.email == user["email"])
        )
        patient = pat_r.scalars().first()
        if not patient:
            return {"beneficiaries": []}

        ben_r = await db.execute(select(Beneficiary).where(Beneficiary.patient_id == patient.id))
        bens = ben_r.scalars().all()

        return {"beneficiaries": [
            {"id": str(b.id), "name": b.name, "relationship": b.relationship or "",
             "phone": b.phone or "", "gender": b.gender or "",
             "blood_group": b.blood_group or "",
             "date_of_birth": str(b.date_of_birth) if b.date_of_birth else ""}
            for b in bens
        ]}


class BeneficiaryRequest(BaseModel):
    name: str
    relationship: str = ""
    phone: str = ""
    email: str = ""
    gender: str = ""
    blood_group: str = ""
    date_of_birth: str = ""


@router.post("/my-beneficiaries")
async def add_beneficiary(req: BeneficiaryRequest, user: dict = Depends(get_current_user)):
    """Add a beneficiary — also registers them as a patient in the system."""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async with async_session() as db:
        pat_r = await db.execute(
            select(Patient).join(User, Patient.user_id == User.id)
            .where(User.email == user["email"])
        )
        patient = pat_r.scalars().first()
        if not patient:
            raise HTTPException(status_code=404, detail="Patient not found.")

        dob = None
        if req.date_of_birth:
            try:
                dob = datetime.strptime(req.date_of_birth, "%Y-%m-%d").date()
            except ValueError:
                pass

        # Generate UHID for the beneficiary
        last = await db.execute(select(Patient).order_by(Patient.uhid.desc()))
        last_patient = last.scalars().first()
        if last_patient:
            last_num = int(last_patient.uhid.split("-")[-1])
            uhid = f"HMS-{datetime.now().year}-{str(last_num + 1).zfill(5)}"
        else:
            uhid = f"HMS-{datetime.now().year}-00001"

        # Create User for the beneficiary
        ben_email = req.email if req.email else f"ben_{uhid.lower().replace('-', '_')}@hms.local"

        # Check if email already exists
        existing = await db.execute(select(User).where(User.email == ben_email))
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail=f"Email '{ben_email}' already registered.")

        ben_user = User(
            id=uuid_lib.uuid4(),
            email=ben_email,
            password_hash=pwd_context.hash("password123"),
            full_name=req.name,
            phone=req.phone,
            role="patient",
            is_active=True
        )
        db.add(ben_user)
        await db.flush()

        # Create Patient record
        ben_patient = Patient(
            id=uuid_lib.uuid4(),
            user_id=ben_user.id,
            uhid=uhid,
            gender=req.gender,
            blood_group=req.blood_group,
            date_of_birth=dob
        )
        db.add(ben_patient)
        await db.flush()

        # Create Beneficiary link
        ben = Beneficiary(
            id=uuid_lib.uuid4(),
            patient_id=patient.id,
            name=req.name,
            relationship=req.relationship,
            phone=req.phone,
            gender=req.gender,
            blood_group=req.blood_group,
            date_of_birth=dob
        )
        db.add(ben)
        await log_action(db, patient.user_id, "ADD_BENEFICIARY", "beneficiary", ben.id, {"name": req.name, "uhid": uhid})
        await db.commit()

    return {"message": f"Beneficiary '{req.name}' added and registered as patient (UHID: {uhid}).", "uhid": uhid}


class BeneficiaryUpdateRequest(BaseModel):
    name: str = ""
    relationship: str = ""
    phone: str = ""
    gender: str = ""
    blood_group: str = ""
    date_of_birth: str = ""


@router.put("/my-beneficiaries/{ben_id}")
async def update_beneficiary(ben_id: str, req: BeneficiaryUpdateRequest, user: dict = Depends(get_current_user)):
    """Update a beneficiary."""
    async with async_session() as db:
        usr_r = await db.execute(select(User).where(User.email == user["email"]))
        usr = usr_r.scalars().first()
        ben_r = await db.execute(select(Beneficiary).where(Beneficiary.id == ben_id))
        ben = ben_r.scalars().first()
        if not ben:
            raise HTTPException(status_code=404, detail="Beneficiary not found.")
        if req.name:
            ben.name = req.name
        if req.relationship:
            ben.relationship = req.relationship
        if req.phone:
            ben.phone = req.phone
        if req.gender:
            ben.gender = req.gender
        if req.blood_group:
            ben.blood_group = req.blood_group
        if req.date_of_birth:
            try:
                ben.date_of_birth = datetime.strptime(req.date_of_birth, "%Y-%m-%d").date()
            except ValueError:
                pass
        await log_action(db, usr.id, "UPDATE_BENEFICIARY", "beneficiary", ben.id, {"name": ben.name})
        await db.commit()
    return {"message": "Beneficiary updated."}


@router.delete("/my-beneficiaries/{ben_id}")
async def delete_beneficiary(ben_id: str, user: dict = Depends(get_current_user)):
    """Delete a beneficiary."""
    async with async_session() as db:
        usr_r = await db.execute(select(User).where(User.email == user["email"]))
        usr = usr_r.scalars().first()
        ben_r = await db.execute(select(Beneficiary).where(Beneficiary.id == ben_id))
        ben = ben_r.scalars().first()
        if not ben:
            raise HTTPException(status_code=404, detail="Beneficiary not found.")
        await log_action(db, usr.id, "DELETE_BENEFICIARY", "beneficiary", ben.id, {"name": ben.name})
        await db.delete(ben)
        await db.commit()
    return {"message": "Beneficiary removed."}


# ─── Request / Response models ──────────────────────────────────────────────

class BookAppointmentRequest(BaseModel):
    patient_uhid: str
    doctor_name: str
    preferred_time: str = ""
    preferred_date: str = ""
    confirm: bool = False


class AppointmentResponse(BaseModel):
    id: str
    patient_uhid: str
    doctor_name: str
    date: str
    slot_time: str
    slot_number: int
    status: str
    priority: str
    is_emergency: bool


# ─── GET /available-slots ───────────────────────────────────────────────────

@router.get("/available-slots")
async def get_available_slots(
    doctor_name: str = Query(..., description="Doctor name (partial match)"),
    date_str: str = Query("", alias="date", description="Date YYYY-MM-DD, defaults to today"),
    user: dict = Depends(get_current_user)
):
    """
    Get all available slots for a doctor on a given date.
    Returns slot numbers, times, and how many bookings remain per slot.
    """
    async with async_session() as db:
        # Find doctor
        doc_r = await db.execute(
            select(Doctor, User).join(User, Doctor.user_id == User.id)
            .where(User.full_name.ilike(f"%{doctor_name}%"))
        )
        doc_row = doc_r.first()
        if not doc_row:
            raise HTTPException(status_code=404, detail=f"Doctor '{doctor_name}' not found.")
        doctor, doc_user = doc_row

        # Parse date
        query_date = date.today()
        if date_str:
            try:
                query_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format. Use YYYY-MM-DD.")

        # Find session
        sess_r = await db.execute(
            select(Session).where(
                Session.doctor_id == doctor.id,
                Session.session_date == query_date,
                Session.status.in_(["scheduled", "active"])
            )
        )
        session = sess_r.scalars().first()
        if not session:
            raise HTTPException(status_code=404, detail=f"No session for Dr. {doc_user.full_name} on {query_date}.")

        # Generate all slots
        all_slots = generate_slot_times(
            session.start_time, session.end_time, session.slot_duration_minutes,
            session.lunch_start, session.lunch_end, session.overtime_minutes
        )

        # Get booked counts per slot
        counts_r = await db.execute(
            select(Appointment.slot_number, func.count(Appointment.id))
            .where(
                Appointment.session_id == session.id,
                Appointment.status.in_(["booked", "checked_in", "in_progress"])
            ).group_by(Appointment.slot_number)
        )
        booked = {r[0]: r[1] for r in counts_r.all()}

        # Filter past slots for today
        min_slot = 1
        if query_date == date.today():
            now = datetime.now()
            start_dt = datetime.combine(query_date, session.start_time)
            diff = (now - start_dt).total_seconds() / 60
            if diff > 0:
                min_slot = int(diff // session.slot_duration_minutes) + 2

        available = []
        for slot in all_slots:
            if slot["slot_number"] < min_slot:
                continue
            count = booked.get(slot["slot_number"], 0)
            if count < session.max_per_slot:
                available.append({
                    "slot_number": slot["slot_number"],
                    "slot_time": str(slot["slot_time"]),
                    "available_positions": session.max_per_slot - count,
                    "max_per_slot": session.max_per_slot,
                })

    return {
        "doctor": doc_user.full_name,
        "date": str(query_date),
        "session_start": str(session.start_time),
        "session_end": str(session.end_time),
        "lunch_break": f"{session.lunch_start}-{session.lunch_end}",
        "delay_minutes": session.delay_minutes,
        "total_available": len(available),
        "slots": available,
    }


# ─── POST /book-appointment ────────────────────────────────────────────────

@router.post("/book-appointment")
async def book_appointment_api(req: BookAppointmentRequest, user: dict = Depends(get_current_user)):
    """
    Book an appointment via REST API.
    Two-step: first call without confirm=True to see proposed slot, then confirm.
    """
    async with async_session() as db:
        # Validate time format
        if req.preferred_time:
            try:
                datetime.strptime(req.preferred_time, "%H:%M").time()
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid time format. Use HH:MM.")

        # Find patient
        pat_r = await db.execute(select(Patient).where(Patient.uhid == req.patient_uhid))
        patient = pat_r.scalars().first()
        if not patient:
            raise HTTPException(status_code=404, detail=f"Patient {req.patient_uhid} not found.")

        # Find doctor
        doc_r = await db.execute(
            select(Doctor, User).join(User, Doctor.user_id == User.id)
            .where(User.full_name.ilike(f"%{req.doctor_name}%"))
        )
        doc_row = doc_r.first()
        if not doc_row:
            raise HTTPException(status_code=404, detail=f"Doctor {req.doctor_name} not found.")
        doctor, doc_user = doc_row

        # Find available session
        session_filter = [
            Session.doctor_id == doctor.id,
            Session.status.in_(["scheduled", "active"]),
        ]
        if req.preferred_date:
            try:
                pref_date = datetime.strptime(req.preferred_date, "%Y-%m-%d").date()
                session_filter.append(Session.session_date == pref_date)
            except ValueError:
                session_filter.append(Session.session_date >= date.today())
        else:
            session_filter.append(Session.session_date >= date.today())

        sess_r = await db.execute(
            select(Session).where(*session_filter)
            .order_by(Session.session_date, Session.start_time)
        )
        sessions = sess_r.scalars().all()
        if not sessions:
            raise HTTPException(status_code=404, detail=f"No available sessions for Dr. {doc_user.full_name}.")

        # Find free slot
        from tools.appointment_tools import find_free_slot
        found = None
        chosen_session = None
        for s in sessions:
            result = await find_free_slot(db, s, req.preferred_time)
            if result:
                found = result
                chosen_session = s
                break

        if not found:
            raise HTTPException(status_code=409, detail="No available slots.")

        slot_number, position, slot_time = found

        if not req.confirm:
            return {
                "status": "pending_confirmation",
                "message": f"Slot available: {slot_time} on {chosen_session.session_date}. Set confirm=true to book.",
                "proposed_slot": {
                    "doctor": doc_user.full_name,
                    "date": str(chosen_session.session_date),
                    "time": str(slot_time),
                    "slot_number": slot_number,
                }
            }

        # Check duplicate
        dup_r = await db.execute(
            select(Appointment).where(
                Appointment.session_id == chosen_session.id,
                Appointment.patient_id == patient.id,
                Appointment.status.in_(["booked", "checked_in", "in_progress"])
            )
        )
        if dup_r.scalars().first():
            raise HTTPException(status_code=409, detail="Patient already has an appointment in this session.")

        # Create appointment
        new_appt = Appointment(
            id=uuid_lib.uuid4(),
            session_id=chosen_session.id,
            patient_id=patient.id,
            booked_by=patient.user_id,
            slot_number=slot_number,
            slot_position=position,
            slot_time=slot_time,
            status="booked"
        )
        db.add(new_appt)
        await log_action(db, patient.user_id, "BOOK", "appointment", new_appt.id,
                        {"uhid": req.patient_uhid, "doctor": doc_user.full_name})
        await db.commit()

    return {
        "status": "booked",
        "appointment": {
            "id": str(new_appt.id),
            "patient_uhid": req.patient_uhid,
            "doctor": doc_user.full_name,
            "date": str(chosen_session.session_date),
            "time": str(slot_time),
            "slot_number": slot_number,
        }
    }


# ─── GET /appointments ──────────────────────────────────────────────────────

@router.get("/appointments")
async def get_appointments(
    patient_uhid: str = Query("", description="Filter by patient UHID"),
    doctor_name: str = Query("", description="Filter by doctor name"),
    date_str: str = Query("", alias="date", description="Filter by date YYYY-MM-DD"),
    status: str = Query("", description="Filter by status (booked, checked_in, completed, cancelled, no_show)"),
    user: dict = Depends(get_current_user)
):
    """Get appointments with optional filters."""
    async with async_session() as db:
        stmt = (
            select(Appointment, Patient, User, Session, Doctor)
            .join(Patient, Appointment.patient_id == Patient.id)
            .join(User, Patient.user_id == User.id)
            .join(Session, Appointment.session_id == Session.id)
            .join(Doctor, Session.doctor_id == Doctor.id)
        )

        if patient_uhid:
            stmt = stmt.where(Patient.uhid == patient_uhid)
        if doctor_name:
            doc_user_alias = select(Doctor.id).join(User, Doctor.user_id == User.id).where(
                User.full_name.ilike(f"%{doctor_name}%"))
            stmt = stmt.where(Session.doctor_id.in_(doc_user_alias))
        if date_str:
            try:
                filter_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                stmt = stmt.where(Session.session_date == filter_date)
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid date format.")
        if status:
            stmt = stmt.where(Appointment.status == status)

        stmt = stmt.order_by(Session.session_date.desc(), Appointment.slot_time)
        result = await db.execute(stmt)
        rows = result.all()

        # Get doctor user names
        appointments = []
        for appt, patient, pat_user, session, doctor in rows:
            doc_user_r = await db.execute(select(User).where(User.id == doctor.user_id))
            doc_user = doc_user_r.scalars().first()
            appointments.append({
                "id": str(appt.id),
                "patient_uhid": patient.uhid,
                "patient_name": pat_user.full_name,
                "doctor_name": doc_user.full_name if doc_user else "Unknown",
                "date": str(session.session_date),
                "slot_time": str(appt.slot_time),
                "slot_number": appt.slot_number,
                "status": appt.status,
                "priority": appt.priority,
                "is_emergency": appt.is_emergency,
            })

    return {"total": len(appointments), "appointments": appointments}
