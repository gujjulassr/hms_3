from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select, func
from datetime import datetime, date, time, timedelta
import uuid as uuid_lib

from config.database import AsyncSessionLocal as async_session
from config.auth import get_current_user
from models.user import User
from models.doctor import Doctor
from models.session import Session
from models.appointment import Appointment
from models.patient import Patient
from services.slot_utils import count_slots, generate_slot_times

router = APIRouter(prefix="/api/doctor", tags=["doctor"])


class ActionRequest(BaseModel):
    session_id: str = ""
    patient_uhid: str = ""
    message: str = ""
    extra_minutes: int = 0
    # Create session fields
    session_date: str = ""
    start_time: str = ""
    end_time: str = ""
    slot_duration: int = 15
    notes: str = ""


# ─── Helper ──────────────────────────────────────────────────────────────────

async def _get_doctor(db, user: dict):
    result = await db.execute(
        select(Doctor, User).join(User, Doctor.user_id == User.id)
        .where(User.email == user["email"])
    )
    row = result.first()
    if not row:
        raise HTTPException(status_code=404, detail="Doctor not found")
    return row  # (Doctor, User)


# ─── Sessions ────────────────────────────────────────────────────────────────

@router.get("/my-sessions")
async def get_my_sessions(user: dict = Depends(get_current_user)):
    async with async_session() as db:
        doctor, doc_user = await _get_doctor(db, user)

        result = await db.execute(
            select(Session).where(
                Session.doctor_id == doctor.id,
                Session.session_date >= date.today(),
                Session.status != "cancelled"
            ).order_by(Session.session_date, Session.start_time)
        )
        sessions = result.scalars().all()

        output = []
        for s in sessions:
            # Count booked appointments
            booked_result = await db.execute(
                select(func.count(Appointment.id)).where(
                    Appointment.session_id == s.id,
                    Appointment.status.in_(["booked", "checked_in", "in_progress"])
                )
            )
            booked_count = booked_result.scalar() or 0

            actual_end = (datetime.combine(s.session_date, s.end_time) +
                         timedelta(minutes=s.overtime_minutes)).time() if s.overtime_minutes > 0 else s.end_time

            output.append({
                "id": str(s.id),
                "date": str(s.session_date),
                "start_time": str(s.start_time),
                "end_time": str(s.end_time),
                "actual_end_time": str(actual_end),
                "lunch_start": str(s.lunch_start),
                "lunch_end": str(s.lunch_end),
                "total_slots": s.total_slots,
                "booked": booked_count,
                "status": s.status,
                "delay_minutes": s.delay_minutes,
                "overtime_minutes": s.overtime_minutes,
                "slot_duration": s.slot_duration_minutes,
            })

    return {"sessions": output}


@router.post("/create-session")
async def create_session_api(request: ActionRequest, user: dict = Depends(get_current_user)):
    async with async_session() as db:
        doctor, doc_user = await _get_doctor(db, user)

        try:
            s_date = datetime.strptime(request.session_date, "%Y-%m-%d").date()
            s_start = datetime.strptime(request.start_time, "%H:%M").time()
            s_end = datetime.strptime(request.end_time, "%H:%M").time()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date/time format. Use YYYY-MM-DD and HH:MM.")

        if s_date < date.today():
            raise HTTPException(status_code=400, detail="Cannot create session in the past.")

        # Check for existing active/scheduled session on same date
        existing = await db.execute(
            select(Session).where(
                Session.doctor_id == doctor.id,
                Session.session_date == s_date,
                Session.status.in_(["scheduled", "active"])
            )
        )
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail=f"Dr. {doc_user.full_name} already has an active session on {s_date}.")

        total_slots = count_slots(s_start, s_end, request.slot_duration)

        new_session = Session(
            id=uuid_lib.uuid4(),
            doctor_id=doctor.id,
            session_date=s_date,
            start_time=s_start,
            end_time=s_end,
            slot_duration_minutes=request.slot_duration,
            total_slots=total_slots,
            status="scheduled"
        )
        db.add(new_session)
        await db.commit()

    return {"message": f"Session created for Dr. {doc_user.full_name} on {s_date}, {s_start}-{s_end}, {total_slots} slots (lunch 13:00-13:30 blocked)."}


@router.post("/activate-session")
async def activate_session_api(user: dict = Depends(get_current_user)):
    async with async_session() as db:
        doctor, doc_user = await _get_doctor(db, user)
        now = datetime.now().time()

        result = await db.execute(
            select(Session).where(
                Session.doctor_id == doctor.id,
                Session.session_date == date.today(),
                Session.status == "scheduled",
                Session.end_time > now
            ).order_by(Session.start_time)
        )
        session = result.scalars().first()
        if not session:
            raise HTTPException(status_code=404, detail="No scheduled session found for today.")

        session.status = "active"
        await db.commit()

    return {"message": f"Session activated for Dr. {doc_user.full_name} ({session.start_time}-{session.end_time})."}


@router.post("/complete-session")
async def complete_session_api(user: dict = Depends(get_current_user)):
    async with async_session() as db:
        doctor, doc_user = await _get_doctor(db, user)

        result = await db.execute(
            select(Session).where(
                Session.doctor_id == doctor.id,
                Session.session_date == date.today(),
                Session.status == "active"
            )
        )
        session = result.scalars().first()
        if not session:
            raise HTTPException(status_code=404, detail="No active session found.")

        # Get all pending appointments
        appt_result = await db.execute(
            select(Appointment, Patient).join(Patient, Appointment.patient_id == Patient.id)
            .where(
                Appointment.session_id == session.id,
                Appointment.status.in_(["booked", "checked_in"])
            )
        )
        pending = appt_result.all()

        no_show_count = 0
        cancelled_count = 0

        from services.notifications.service import notify_no_show
        for appt, patient in pending:
            if appt.status == "booked":
                appt.status = "no_show"
                patient.risk_score = (patient.risk_score or 0) + 20
                no_show_count += 1
                pat_user_r = await db.execute(select(User).where(User.id == patient.user_id))
                pat_user = pat_user_r.scalars().first()
                if pat_user:
                    await notify_no_show(pat_user.email, pat_user.full_name,
                                       doc_user.full_name, patient.risk_score)
            elif appt.status == "checked_in":
                # No risk penalty for checked-in patients
                appt.status = "cancelled"
                cancelled_count += 1

        session.status = "completed"
        await db.commit()

    return {"message": f"Session completed. No-shows: {no_show_count}, Cancelled: {cancelled_count}."}


@router.post("/extend-session")
async def extend_session_api(request: ActionRequest, user: dict = Depends(get_current_user)):
    async with async_session() as db:
        doctor, doc_user = await _get_doctor(db, user)

        result = await db.execute(
            select(Session).where(
                Session.doctor_id == doctor.id,
                Session.session_date == date.today(),
                Session.status == "active"
            )
        )
        session = result.scalars().first()
        if not session:
            raise HTTPException(status_code=404, detail="No active session to extend.")

        # extra_minutes = total overtime from original end time
        session.overtime_minutes = request.extra_minutes

        # Recalculate total slots with overtime, excluding lunch
        session.total_slots = count_slots(
            session.start_time, session.end_time, session.slot_duration_minutes,
            session.lunch_start, session.lunch_end, session.overtime_minutes
        )
        await db.commit()

        actual_end = (datetime.combine(session.session_date, session.end_time) +
                     timedelta(minutes=session.overtime_minutes)).time()

    return {"message": f"Session extended to {actual_end}. Total slots: {session.total_slots}."}


@router.post("/cancel-session")
async def cancel_session_api(request: ActionRequest, user: dict = Depends(get_current_user)):
    async with async_session() as db:
        doctor, doc_user = await _get_doctor(db, user)

        if request.session_id:
            result = await db.execute(
                select(Session).where(Session.id == uuid_lib.UUID(request.session_id), Session.status == "scheduled")
            )
        else:
            result = await db.execute(
                select(Session).where(
                    Session.doctor_id == doctor.id,
                    Session.status == "scheduled"
                ).order_by(Session.session_date)
            )
        session = result.scalars().first()
        if not session:
            raise HTTPException(status_code=404, detail="No scheduled session found.")

        # Cancel all appointments
        appt_result = await db.execute(
            select(Appointment).where(
                Appointment.session_id == session.id,
                Appointment.status.in_(["booked", "checked_in"])
            )
        )
        appts = appt_result.scalars().all()
        cancelled = 0
        from services.notifications.service import notify_session_cancelled
        for appt in appts:
            appt.status = "cancelled"
            cancelled += 1
            pat_r = await db.execute(
                select(Patient, User).join(User, Patient.user_id == User.id)
                .where(Patient.id == appt.patient_id)
            )
            pat_row = pat_r.first()
            if pat_row:
                await notify_session_cancelled(pat_row[1].email, pat_row[1].full_name,
                                              doc_user.full_name, str(session.session_date))

        session.status = "cancelled"
        await db.commit()

    return {"message": f"Session cancelled. {cancelled} appointments cancelled."}


# ─── Queue & Patient Actions ────────────────────────────────────────────────

@router.get("/queue")
async def get_queue_api(user: dict = Depends(get_current_user)):
    """Get current queue for doctor's active session."""
    async with async_session() as db:
        doctor, doc_user = await _get_doctor(db, user)

        result = await db.execute(
            select(Session).where(
                Session.doctor_id == doctor.id,
                Session.session_date == date.today(),
                Session.status.in_(["active", "scheduled"])
            ).order_by(Session.start_time)
        )
        session = result.scalars().first()
        if not session:
            return {"session": None, "emergency": [], "in_progress": [], "waiting": [], "booked": [], "delay_minutes": 0}

        # Emergency queue
        emerg_r = await db.execute(
            select(Appointment, Patient, User)
            .join(Patient, Appointment.patient_id == Patient.id)
            .join(User, Patient.user_id == User.id)
            .where(
                Appointment.session_id == session.id,
                Appointment.is_emergency == True,
                Appointment.status.in_(["checked_in", "in_progress"])
            ).order_by(Appointment.checked_in_at)
        )
        emergency = [_format_queue_item(r, session.delay_minutes) for r in emerg_r.all()]

        # In-progress (with doctor)
        prog_r = await db.execute(
            select(Appointment, Patient, User)
            .join(Patient, Appointment.patient_id == Patient.id)
            .join(User, Patient.user_id == User.id)
            .where(
                Appointment.session_id == session.id,
                Appointment.is_emergency == False,
                Appointment.status == "in_progress"
            ).order_by(Appointment.started_at)
        )
        in_progress = [_format_queue_item(r, session.delay_minutes) for r in prog_r.all()]

        # Waiting (checked in, not yet called)
        wait_r = await db.execute(
            select(Appointment, Patient, User)
            .join(Patient, Appointment.patient_id == Patient.id)
            .join(User, Patient.user_id == User.id)
            .where(
                Appointment.session_id == session.id,
                Appointment.is_emergency == False,
                Appointment.status == "checked_in"
            ).order_by(Appointment.slot_number, Appointment.slot_position)
        )
        waiting = [_format_queue_item(r, session.delay_minutes) for r in wait_r.all()]

        # Booked (not yet checked in)
        book_r = await db.execute(
            select(Appointment, Patient, User)
            .join(Patient, Appointment.patient_id == Patient.id)
            .join(User, Patient.user_id == User.id)
            .where(
                Appointment.session_id == session.id,
                Appointment.is_emergency == False,
                Appointment.status == "booked"
            ).order_by(Appointment.slot_number)
        )
        booked = [_format_queue_item(r, session.delay_minutes) for r in book_r.all()]

    return {
        "session": {
            "id": str(session.id),
            "start_time": str(session.start_time),
            "end_time": str(session.end_time),
            "actual_end_time": str((datetime.combine(date.today(), session.end_time) +
                                   timedelta(minutes=session.overtime_minutes)).time()),
            "status": session.status,
            "delay_minutes": session.delay_minutes,
            "overtime_minutes": session.overtime_minutes,
            "total_slots": session.total_slots,
        },
        "emergency": emergency,
        "in_progress": in_progress,
        "waiting": waiting,
        "booked": booked,
        "delay_minutes": session.delay_minutes,
    }


def _format_queue_item(row, delay_minutes: int) -> dict:
    appt, patient, user = row
    # Calculate expected time (slot_time + delay)
    expected = (datetime.combine(date.today(), appt.slot_time) +
               timedelta(minutes=delay_minutes)).time() if not appt.is_emergency else appt.slot_time
    return {
        "uhid": patient.uhid,
        "name": user.full_name,
        "slot_number": appt.slot_number,
        "slot_time": str(appt.slot_time),
        "expected_time": str(expected),
        "status": appt.status,
        "priority": appt.priority,
        "is_emergency": appt.is_emergency,
        "checked_in_at": str(appt.checked_in_at) if appt.checked_in_at else None,
        "started_at": str(appt.started_at) if appt.started_at else None,
    }


@router.post("/checkin-patient")
async def checkin_patient_api(request: ActionRequest, user: dict = Depends(get_current_user)):
    """Check in a patient — changes status from booked to checked_in."""
    async with async_session() as db:
        result = await db.execute(
            select(Appointment, Patient)
            .join(Patient, Appointment.patient_id == Patient.id)
            .where(Patient.uhid == request.patient_uhid, Appointment.status == "booked")
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail=f"No booked appointment found for {request.patient_uhid}")

        appt, patient = row

        # Verify session is active
        sess_r = await db.execute(select(Session).where(Session.id == appt.session_id))
        sess = sess_r.scalars().first()
        if not sess or sess.status != "active":
            raise HTTPException(status_code=400, detail="Cannot check in — session is not active.")

        appt.status = "checked_in"
        appt.checked_in_at = datetime.now()
        await db.commit()

    return {"message": f"Patient {request.patient_uhid} checked in at {appt.checked_in_at.strftime('%H:%M')}."}


@router.post("/cancel-appointment")
async def cancel_appointment_api(request: ActionRequest, user: dict = Depends(get_current_user)):
    """Cancel a patient's booked appointment."""
    async with async_session() as db:
        result = await db.execute(
            select(Appointment, Patient)
            .join(Patient, Appointment.patient_id == Patient.id)
            .where(Patient.uhid == request.patient_uhid, Appointment.status.in_(["booked", "checked_in"]))
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail=f"No active appointment found for {request.patient_uhid}")

        appt, patient = row
        appt.status = "cancelled"
        patient.risk_score = (patient.risk_score or 0) + 10
        await db.commit()

    return {"message": f"Appointment for {request.patient_uhid} cancelled."}


@router.post("/call-patient")
async def call_patient_api(request: ActionRequest, user: dict = Depends(get_current_user)):
    """Doctor calls a patient — changes status to in_progress."""
    async with async_session() as db:
        result = await db.execute(
            select(Appointment, Patient)
            .join(Patient, Appointment.patient_id == Patient.id)
            .where(Patient.uhid == request.patient_uhid, Appointment.status == "checked_in")
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail=f"No checked-in patient found: {request.patient_uhid}")

        appt, patient = row
        appt.status = "in_progress"
        appt.called_at = datetime.now()
        appt.started_at = datetime.now()
        await db.commit()

    return {"message": f"Patient {request.patient_uhid} called in."}


@router.post("/complete-appointment")
async def complete_appointment_api(request: ActionRequest, user: dict = Depends(get_current_user)):
    """Complete a consultation. Updates delay dynamically."""
    async with async_session() as db:
        result = await db.execute(
            select(Appointment, Patient)
            .join(Patient, Appointment.patient_id == Patient.id)
            .where(Patient.uhid == request.patient_uhid, Appointment.status == "in_progress")
        )
        row = result.first()
        if not row:
            raise HTTPException(status_code=404, detail=f"No in-progress appointment for {request.patient_uhid}")

        appt, patient = row
        appt.status = "completed"
        appt.completed_at = datetime.now()
        if request.notes:
            appt.notes = request.notes

        # Dynamic delay calculation
        session_r = await db.execute(select(Session).where(Session.id == appt.session_id))
        session = session_r.scalars().first()

        if session and appt.started_at:
            actual_duration = (appt.completed_at - appt.started_at).total_seconds() / 60
            slot_duration = session.slot_duration_minutes

            if actual_duration > slot_duration:
                # Ran over — increase delay
                extra = int(actual_duration - slot_duration)
                session.delay_minutes += extra
            elif actual_duration < slot_duration and session.delay_minutes > 0:
                # Finished early — reduce delay (catch up)
                saved = int(slot_duration - actual_duration)
                session.delay_minutes = max(0, session.delay_minutes - saved)

        await db.commit()

        from services.notifications.service import notify_feedback
        pat_user_r = await db.execute(select(User).where(User.id == patient.user_id))
        pat_user = pat_user_r.scalars().first()
        doc_user_r = await db.execute(
            select(User).join(Doctor, Doctor.user_id == User.id)
            .where(Doctor.id == session.doctor_id)
        )
        doc_user = doc_user_r.scalars().first()

    if pat_user and doc_user:
        await notify_feedback(pat_user.email, pat_user.full_name, doc_user.full_name)

    return {"message": f"Appointment completed. Delay: {session.delay_minutes}min.", "delay_minutes": session.delay_minutes}
