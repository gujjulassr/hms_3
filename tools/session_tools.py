from langchain_core.tools import tool
from sqlalchemy import select
from models.session import Session
from models.appointment import Appointment
from models.patient import Patient
from models.doctor import Doctor
from models.user import User
from config.database import AsyncSessionLocal as async_session
import uuid
from datetime import datetime, date, time, timedelta
from services.audit import log_action
from services.slot_utils import count_slots, generate_slot_times


@tool
async def check_availability(doctor_name: str, check_date: str = "") -> str:
    """Check available sessions for a doctor. Use 'today', 'tomorrow', or 'YYYY-MM-DD'. Empty shows all future."""
    async with async_session() as db:
        if check_date == "today":
            query_date = date.today()
        elif check_date == "tomorrow":
            query_date = date.today() + timedelta(days=1)
        elif check_date:
            try:
                query_date = datetime.strptime(check_date, "%Y-%m-%d").date()
            except ValueError:
                query_date = None
        else:
            query_date = None

        stmt = (select(Session, Doctor, User)
                .join(Doctor, Session.doctor_id == Doctor.id)
                .join(User, Doctor.user_id == User.id)
                .where(User.full_name.ilike(f"%{doctor_name}%"), Session.status.in_(["scheduled", "active"])))

        if query_date:
            stmt = stmt.where(Session.session_date == query_date)
        else:
            stmt = stmt.where(Session.session_date >= date.today())

        result = await db.execute(stmt)
        rows = result.all()

    if not rows:
        return f"No available sessions for {doctor_name}."

    output = ""
    for session, doctor, user in rows:
        actual_end = (datetime.combine(session.session_date, session.end_time) +
                     timedelta(minutes=session.overtime_minutes)).time() if session.overtime_minutes > 0 else session.end_time
        output += (f"Doctor: {user.full_name}, Date: {session.session_date}, "
                  f"Time: {session.start_time}-{actual_end}, Slots: {session.total_slots}, "
                  f"Slot Duration: {session.slot_duration_minutes}min, Lunch: {session.lunch_start}-{session.lunch_end}\n")
    return output


@tool
async def create_session(doctor_name: str, session_date: str, start_time: str, end_time: str,
                         slot_duration: int = 15, max_per_slot: int = 2) -> str:
    """Create a new session for a doctor. One per day. Date: YYYY-MM-DD, Time: HH:MM. Lunch 13:00-13:30 auto-blocked."""
    async with async_session() as db:
        result = await db.execute(
            select(Doctor, User).join(User, Doctor.user_id == User.id)
            .where(User.full_name.ilike(f"%{doctor_name}%"))
        )
        row = result.first()
        if not row:
            return f"Doctor {doctor_name} not found."
        doctor, doc_user = row

        try:
            s_date = datetime.strptime(session_date, "%Y-%m-%d").date()
            s_start = datetime.strptime(start_time, "%H:%M").time()
            s_end = datetime.strptime(end_time, "%H:%M").time()
        except ValueError:
            return "Invalid format. Use YYYY-MM-DD for date and HH:MM for time."

        if s_date < date.today():
            return "Cannot create session in the past."

        # One session per day check
        existing = await db.execute(
            select(Session).where(
                Session.doctor_id == doctor.id,
                Session.session_date == s_date,
                Session.status.in_(["scheduled", "active"])
            )
        )
        if existing.scalars().first():
            return f"Dr. {doc_user.full_name} already has an active session on {s_date}."

        total_slots = count_slots(s_start, s_end, slot_duration)

        new_session = Session(
            id=uuid.uuid4(),
            doctor_id=doctor.id,
            session_date=s_date,
            start_time=s_start,
            end_time=s_end,
            slot_duration_minutes=slot_duration,
            max_per_slot=max_per_slot,
            total_slots=total_slots,
            status="scheduled"
        )
        db.add(new_session)
        await log_action(db, doc_user.id, "CREATE_SESSION", "session", new_session.id,
                        {"doctor": doc_user.full_name, "date": str(s_date)})
        await db.commit()

    return f"Session created for Dr. {doc_user.full_name} on {s_date}, {s_start}-{s_end}, {total_slots} slots (lunch 13:00-13:30 blocked)."


@tool
async def activate_session(doctor_name: str) -> str:
    """Activate a doctor's scheduled session for today."""
    async with async_session() as db:
        now = datetime.now().time()
        result = await db.execute(
            select(Session, Doctor, User)
            .join(Doctor, Session.doctor_id == Doctor.id)
            .join(User, Doctor.user_id == User.id)
            .where(
                User.full_name.ilike(f"%{doctor_name}%"),
                Session.session_date == date.today(),
                Session.status == "scheduled",
                Session.end_time > now
            ).order_by(Session.start_time)
        )
        row = result.first()
        if not row:
            return f"No scheduled session found for {doctor_name} today."

        session, doctor, doc_user = row
        session.status = "active"
        await log_action(db, doc_user.id, "ACTIVATE_SESSION", "session", session.id, {"doctor": doc_user.full_name})
        await db.commit()

    return f"Session activated for Dr. {doc_user.full_name} ({session.start_time}-{session.end_time})."


@tool
async def complete_session(doctor_name: str) -> str:
    """Complete a doctor's active session. Booked→no_show (risk+20), checked_in→cancelled (no risk)."""
    async with async_session() as db:
        result = await db.execute(
            select(Session, Doctor, User)
            .join(Doctor, Session.doctor_id == Doctor.id)
            .join(User, Doctor.user_id == User.id)
            .where(
                User.full_name.ilike(f"%{doctor_name}%"),
                Session.session_date == date.today(),
                Session.status == "active"
            )
        )
        row = result.first()
        if not row:
            return f"No active session found for {doctor_name} today."

        session, doctor, doc_user = row

        appt_result = await db.execute(
            select(Appointment, Patient).join(Patient, Appointment.patient_id == Patient.id)
            .where(Appointment.session_id == session.id, Appointment.status.in_(["booked", "checked_in"]))
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
                    await notify_no_show(pat_user.email, pat_user.full_name, doc_user.full_name, patient.risk_score)
            elif appt.status == "checked_in":
                appt.status = "cancelled"
                cancelled_count += 1

        session.status = "completed"
        await log_action(db, doc_user.id, "COMPLETE_SESSION", "session", session.id,
                        {"no_shows": no_show_count, "cancelled": cancelled_count})
        await db.commit()

    return f"Session completed for Dr. {doc_user.full_name}. No-shows: {no_show_count}, Cancelled: {cancelled_count}."


@tool
async def extend_session(doctor_name: str, new_end_time: str) -> str:
    """Extend a doctor's active session. Provide new end time like '19:00'."""
    async with async_session() as db:
        result = await db.execute(
            select(Session, Doctor, User)
            .join(Doctor, Session.doctor_id == Doctor.id)
            .join(User, Doctor.user_id == User.id)
            .where(
                User.full_name.ilike(f"%{doctor_name}%"),
                Session.session_date >= date.today(),
                Session.status == "active"
            )
        )
        row = result.first()
        if not row:
            return f"No active session found for {doctor_name}."

        session, doctor, doc_user = row

        new_end = datetime.strptime(new_end_time, "%H:%M").time()
        original_end = session.end_time
        overtime = (datetime.combine(session.session_date, new_end) -
                   datetime.combine(session.session_date, original_end)).total_seconds() / 60

        if overtime <= 0:
            return f"New end time must be after original end time ({original_end})."

        session.overtime_minutes = int(overtime)
        session.total_slots = count_slots(
            session.start_time, session.end_time, session.slot_duration_minutes,
            session.lunch_start, session.lunch_end, session.overtime_minutes
        )
        await log_action(db, doc_user.id, "EXTEND_SESSION", "session", session.id,
                        {"overtime": session.overtime_minutes})
        await db.commit()

    actual_end = (datetime.combine(session.session_date, session.end_time) +
                 timedelta(minutes=session.overtime_minutes))
    return f"Session extended for Dr. {doc_user.full_name}. New end time: {actual_end.time()}. Total slots: {session.total_slots}."


@tool
async def cancel_session(doctor_name: str, session_id: str = "") -> str:
    """Cancel a doctor's scheduled session. Optionally pass session_id. All booked appointments will be cancelled."""
    async with async_session() as db:
        doc_r = await db.execute(
            select(Doctor, User).join(User, Doctor.user_id == User.id)
            .where(User.full_name.ilike(f"%{doctor_name}%"))
        )
        doc_row = doc_r.first()
        if not doc_row:
            return f"Doctor {doctor_name} not found."
        doctor, doc_user = doc_row

        if session_id:
            import uuid as uuid_mod
            result = await db.execute(
                select(Session).where(
                    Session.id == uuid_mod.UUID(session_id),
                    Session.status == "scheduled"
                )
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
            return f"No scheduled session found for Dr. {doc_user.full_name}."

        # Cancel all booked appointments
        appt_result = await db.execute(
            select(Appointment).where(
                Appointment.session_id == session.id,
                Appointment.status.in_(["booked", "checked_in"])
            )
        )
        appts = appt_result.scalars().all()
        cancelled = 0
        for appt in appts:
            appt.status = "cancelled"
            cancelled += 1

        session.status = "cancelled"
        await log_action(db, doc_user.id, "CANCEL_SESSION", "session", session.id,
                        {"doctor": doc_user.full_name, "cancelled_appointments": cancelled})
        await db.commit()

    return f"Session cancelled for Dr. {doc_user.full_name} on {session.session_date}. {cancelled} appointments cancelled."


@tool
async def get_my_sessions(doctor_name: str, session_date: str = "") -> str:
    """Get a doctor's sessions. Empty shows today + upcoming. Use 'today', 'tomorrow', or YYYY-MM-DD."""
    async with async_session() as db:
        doc_r = await db.execute(
            select(Doctor, User).join(User, Doctor.user_id == User.id)
            .where(User.full_name.ilike(f"%{doctor_name}%"))
        )
        doc_row = doc_r.first()
        if not doc_row:
            return f"Doctor {doctor_name} not found."
        doctor, doc_user = doc_row

        specific_date = None
        if session_date == "tomorrow":
            specific_date = date.today() + timedelta(days=1)
        elif session_date == "today":
            specific_date = date.today()
        elif session_date:
            try:
                specific_date = datetime.strptime(session_date, "%Y-%m-%d").date()
            except ValueError:
                specific_date = date.today()

        if specific_date:
            sess_r = await db.execute(
                select(Session).where(
                    Session.doctor_id == doctor.id,
                    Session.session_date == specific_date,
                    Session.status != "cancelled"
                ).order_by(Session.start_time)
            )
        else:
            sess_r = await db.execute(
                select(Session).where(
                    Session.doctor_id == doctor.id,
                    Session.session_date >= date.today(),
                    Session.status != "cancelled"
                ).order_by(Session.session_date, Session.start_time)
            )
        sessions = sess_r.scalars().all()

    if not sessions:
        return f"No sessions for Dr. {doc_user.full_name}."

    output = f"Sessions for Dr. {doc_user.full_name}:\n\n"
    for s in sessions:
        actual_end = (datetime.combine(s.session_date, s.end_time) +
                     timedelta(minutes=s.overtime_minutes)).time() if s.overtime_minutes > 0 else s.end_time
        label = "Today" if s.session_date == date.today() else str(s.session_date)
        output += f"  {label}: {s.start_time}-{actual_end} | Status: {s.status.upper()} | Slots: {s.total_slots}"
        if s.delay_minutes > 0:
            output += f" | Delay: {s.delay_minutes}min"
        if s.overtime_minutes > 0:
            output += f" | Overtime: {s.overtime_minutes}min"
        output += "\n"
    return output


@tool
async def get_my_patients(doctor_name: str, patient_date: str = "") -> str:
    """Get all patients for a doctor. Use 'today', 'tomorrow', YYYY-MM-DD, or empty for today."""
    async with async_session() as db:
        doc_r = await db.execute(
            select(Doctor, User).join(User, Doctor.user_id == User.id)
            .where(User.full_name.ilike(f"%{doctor_name}%"))
        )
        doc_row = doc_r.first()
        if not doc_row:
            return f"Doctor {doctor_name} not found."
        doctor, doc_user = doc_row

        if patient_date == "tomorrow":
            query_date = date.today() + timedelta(days=1)
        elif patient_date:
            try:
                query_date = datetime.strptime(patient_date, "%Y-%m-%d").date()
            except ValueError:
                query_date = date.today()
        else:
            query_date = date.today()

        appt_r = await db.execute(
            select(Appointment, Patient, User, Session)
            .join(Patient, Appointment.patient_id == Patient.id)
            .join(User, Patient.user_id == User.id)
            .join(Session, Appointment.session_id == Session.id)
            .where(Session.doctor_id == doctor.id, Session.session_date == query_date)
            .order_by(Appointment.slot_number)
        )
        rows = appt_r.all()

    if not rows:
        return f"No patients for Dr. {doc_user.full_name} on {query_date}."

    completed = sum(1 for r in rows if r[0].status == "completed")
    cancelled = sum(1 for r in rows if r[0].status == "cancelled")
    no_show = sum(1 for r in rows if r[0].status == "no_show")
    waiting = sum(1 for r in rows if r[0].status in ["booked", "checked_in"])
    emergency = sum(1 for r in rows if r[0].is_emergency)

    output = (f"Patients for Dr. {doc_user.full_name} on {query_date} "
             f"(Total: {len(rows)}, Completed: {completed}, Cancelled: {cancelled}, "
             f"No-show: {no_show}, Waiting: {waiting}, Emergency: {emergency}):\n\n")
    for appt, patient, pat_user, session in rows:
        e_tag = " [EMERGENCY]" if appt.is_emergency else ""
        p_tag = f" Priority: {appt.priority}" if appt.priority != "NORMAL" else ""
        output += f"UHID: {patient.uhid}, Name: {pat_user.full_name}, Time: {appt.slot_time}, Status: {appt.status.upper()}{e_tag}{p_tag}\n"
    return output
