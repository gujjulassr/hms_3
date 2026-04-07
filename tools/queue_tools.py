from langchain_core.tools import tool
from sqlalchemy import select
from models.appointment import Appointment
from models.patient import Patient
from models.user import User
from models.session import Session
from models.doctor import Doctor
from models.audit_log import AuditLog
from config.database import AsyncSessionLocal as async_session
from datetime import datetime, date, timedelta
from services.audit import log_action
from services.notifications.service import notify_checkin, notify_feedback


@tool
async def checkin_patient(patient_uhid: str) -> str:
    """Check in a patient who has arrived. Changes status from booked to checked_in.
    Use UHID not patient name."""
    async with async_session() as db:
        result = await db.execute(
            select(Appointment, Patient)
            .join(Patient, Appointment.patient_id == Patient.id)
            .where(Patient.uhid == patient_uhid, Appointment.status == "booked")
        )
        row = result.first()
        if not row:
            return f"No booked appointment found for {patient_uhid}."

        appt, patient = row

        # Check if session is active
        sess_r = await db.execute(select(Session).where(Session.id == appt.session_id))
        sess = sess_r.scalars().first()
        if not sess or sess.status != "active":
            return f"Cannot check in — session is not active. Status: {sess.status if sess else 'not found'}."

        appt.status = "checked_in"
        appt.checked_in_at = datetime.now()

        await log_action(db, patient.user_id, "CHECKIN", "appointment", appt.id, {"uhid": patient_uhid})

        pat_user_r = await db.execute(select(User).where(User.id == patient.user_id))
        pat_user = pat_user_r.scalars().first()
        doc_user_r = await db.execute(
            select(User).join(Doctor, Doctor.user_id == User.id)
            .join(Session, Session.doctor_id == Doctor.id)
            .where(Session.id == appt.session_id)
        )
        doc_user = doc_user_r.scalars().first()
        await db.commit()

    if pat_user:
        doc_name = doc_user.full_name if doc_user else "Doctor"
        wait = sess.delay_minutes if sess else 15
        await notify_checkin(pat_user.email, pat_user.full_name, doc_name, wait)

    return f"Patient {patient_uhid} checked in at {appt.checked_in_at.strftime('%H:%M')}."


@tool
async def get_queue(doctor_name: str) -> str:
    """Get the current queue for a doctor's active session, sorted by slot and priority."""
    async with async_session() as db:
        result = await db.execute(
            select(Session, Doctor, User)
            .join(Doctor, Session.doctor_id == Doctor.id)
            .join(User, Doctor.user_id == User.id)
            .where(
                User.full_name.ilike(f"%{doctor_name}%"),
                Session.session_date == date.today(),
                Session.status.in_(["active", "scheduled"])
            )
        )
        session_row = result.first()
        if not session_row:
            return f"No active session found for {doctor_name} today."

        session, doctor, doc_user = session_row

        # Emergency queue
        emerg_r = await db.execute(
            select(Appointment, Patient, User)
            .join(Patient, Appointment.patient_id == Patient.id)
            .join(User, Patient.user_id == User.id)
            .where(
                Appointment.session_id == session.id,
                Appointment.status.in_(["checked_in", "in_progress"]),
                Appointment.is_emergency == True
            ).order_by(Appointment.checked_in_at)
        )
        emerg_rows = emerg_r.all()

        # Normal queue (checked_in + in_progress)
        normal_r = await db.execute(
            select(Appointment, Patient, User)
            .join(Patient, Appointment.patient_id == Patient.id)
            .join(User, Patient.user_id == User.id)
            .where(
                Appointment.session_id == session.id,
                Appointment.status.in_(["checked_in", "in_progress"]),
                Appointment.is_emergency == False
            ).order_by(Appointment.slot_number)
        )
        normal_rows = normal_r.all()

        output = f"--- Queue for Dr. {doc_user.full_name} (Delay: {session.delay_minutes}min) ---\n\n"

        if emerg_rows:
            output += "EMERGENCY QUEUE:\n"
            for appt, patient, user in emerg_rows:
                output += f"  [{appt.status.upper()}] {patient.uhid} - {user.full_name} (Priority: {appt.priority})\n"
            output += "\n"

        if normal_rows:
            output += "NORMAL QUEUE:\n"
            for appt, patient, user in normal_rows:
                expected = (datetime.combine(date.today(), appt.slot_time) +
                           timedelta(minutes=session.delay_minutes)).time()
                output += f"  [{appt.status.upper()}] {patient.uhid} - {user.full_name} (Slot {appt.slot_number}, Scheduled: {appt.slot_time}, Expected: {expected})\n"
        else:
            output += "NORMAL QUEUE: Empty\n"

        if not emerg_rows and not normal_rows:
            output += "No patients in queue.\n"

    return output


@tool
async def call_next(doctor_name: str) -> str:
    """Suggest the next patient for the doctor. Emergency patients first, then by slot order."""
    async with async_session() as db:
        result = await db.execute(
            select(Session, Doctor, User)
            .join(Doctor, Session.doctor_id == Doctor.id)
            .join(User, Doctor.user_id == User.id)
            .where(
                User.full_name.ilike(f"%{doctor_name}%"),
                Session.session_date == date.today(),
                Session.status.in_(["active", "scheduled"])
            )
        )
        session_row = result.first()
        if not session_row:
            return f"No active session found for {doctor_name} today."

        session, doctor, doc_user = session_row

        # Check emergency first
        emerg_r = await db.execute(
            select(Appointment, Patient, User)
            .join(Patient, Appointment.patient_id == Patient.id)
            .join(User, Patient.user_id == User.id)
            .where(
                Appointment.session_id == session.id,
                Appointment.status == "checked_in",
                Appointment.is_emergency == True
            ).order_by(Appointment.checked_in_at)
        )
        emerg = emerg_r.first()
        if emerg:
            appt, patient, user = emerg
            return f"[EMERGENCY] Next: {patient.uhid} - {user.full_name} (Priority: {appt.priority})"

        # Then normal queue
        normal_r = await db.execute(
            select(Appointment, Patient, User)
            .join(Patient, Appointment.patient_id == Patient.id)
            .join(User, Patient.user_id == User.id)
            .where(
                Appointment.session_id == session.id,
                Appointment.status == "checked_in",
                Appointment.is_emergency == False
            ).order_by(Appointment.slot_number)
        )
        normal = normal_r.first()
        if normal:
            appt, patient, user = normal
            return f"Next: {patient.uhid} - {user.full_name} (Slot {appt.slot_number}, Time: {appt.slot_time})"

    return "No patients waiting in the queue."


@tool
async def call_patient(patient_uhid: str) -> str:
    """Doctor calls a specific patient. Changes status from checked_in to in_progress.
    Use UHID not patient name."""
    async with async_session() as db:
        result = await db.execute(
            select(Appointment, Patient)
            .join(Patient, Appointment.patient_id == Patient.id)
            .where(Patient.uhid == patient_uhid, Appointment.status == "checked_in")
        )
        row = result.first()
        if not row:
            return f"No checked-in appointment found for {patient_uhid}."

        appt, patient = row
        appt.status = "in_progress"
        appt.called_at = datetime.now()
        appt.started_at = datetime.now()

        await log_action(db, patient.user_id, "CALL", "appointment", appt.id, {"uhid": patient_uhid})
        await db.commit()

    return f"Patient {patient_uhid} called in. Consultation started at {appt.started_at.strftime('%H:%M')}."


@tool
async def complete_appointment(patient_uhid: str, notes: str = "") -> str:
    """Mark a patient's appointment as completed. Updates delay dynamically.
    Use UHID not patient name."""
    async with async_session() as db:
        result = await db.execute(
            select(Appointment, Patient)
            .join(Patient, Appointment.patient_id == Patient.id)
            .where(Patient.uhid == patient_uhid, Appointment.status == "in_progress")
        )
        row = result.first()
        if not row:
            return f"No in-progress appointment found for {patient_uhid}."

        appt, patient = row
        appt.status = "completed"
        appt.completed_at = datetime.now()
        if notes:
            appt.notes = notes

        # Dynamic delay update
        sess_r = await db.execute(select(Session).where(Session.id == appt.session_id))
        sess = sess_r.scalars().first()
        if sess and appt.started_at:
            actual_duration = (appt.completed_at - appt.started_at).total_seconds() / 60
            slot_duration = sess.slot_duration_minutes
            if actual_duration > slot_duration:
                extra = int(actual_duration - slot_duration)
                sess.delay_minutes += extra
            elif actual_duration < slot_duration and sess.delay_minutes > 0:
                saved = int(slot_duration - actual_duration)
                sess.delay_minutes = max(0, sess.delay_minutes - saved)

        await log_action(db, patient.user_id, "COMPLETE", "appointment", appt.id, {"uhid": patient_uhid, "notes": notes})

        pat_user_r = await db.execute(select(User).where(User.id == patient.user_id))
        pat_user = pat_user_r.scalars().first()
        doc_user_r = await db.execute(
            select(User).join(Doctor, Doctor.user_id == User.id)
            .join(Session, Session.doctor_id == Doctor.id)
            .where(Session.id == appt.session_id)
        )
        doc_user = doc_user_r.scalars().first()
        await db.commit()

    if pat_user:
        doc_name = doc_user.full_name if doc_user else "Doctor"
        await notify_feedback(pat_user.email, pat_user.full_name, doc_name)

    delay_info = f" Current delay: {sess.delay_minutes}min." if sess else ""
    return f"Appointment completed for {patient_uhid} at {appt.completed_at.strftime('%H:%M')}.{delay_info}"


@tool
async def emergency_book(patient_uhid: str, doctor_name: str) -> str:
    """Book an emergency appointment. Use patient UHID (not name). Bypasses normal slots, goes to emergency queue."""
    import uuid
    async with async_session() as db:
        patient_r = await db.execute(select(Patient).where(Patient.uhid == patient_uhid))
        patient = patient_r.scalars().first()
        if not patient:
            return f"Patient with UHID {patient_uhid} not found."

        result = await db.execute(
            select(Session, Doctor, User)
            .join(Doctor, Session.doctor_id == Doctor.id)
            .join(User, Doctor.user_id == User.id)
            .where(
                User.full_name.ilike(f"%{doctor_name}%"),
                Session.session_date == date.today(),
                Session.status.in_(["active", "scheduled"])
            )
        )
        session_row = result.first()
        if not session_row:
            return f"No active session found for {doctor_name} today."

        session, doctor, doc_user = session_row

        new_appt = Appointment(
            id=uuid.uuid4(),
            session_id=session.id,
            patient_id=patient.id,
            booked_by=patient.user_id,
            slot_number=0,
            slot_position=1,
            slot_time=session.start_time,
            status="checked_in",
            priority="CRITICAL",
            is_emergency=True,
            checked_in_at=datetime.now()
        )
        db.add(new_appt)
        await log_action(db, patient.user_id, "EMERGENCY", "appointment", new_appt.id,
                        {"uhid": patient_uhid, "doctor": doc_user.full_name})
        await db.commit()

    return f"Emergency appointment booked for {patient_uhid} with Dr. {doc_user.full_name}. Added to emergency queue."


@tool
async def set_priority(patient_uhid: str, priority: str) -> str:
    """Set priority for a patient's appointment. Priority: NORMAL, HIGH, or CRITICAL."""
    if priority not in ["NORMAL", "HIGH", "CRITICAL"]:
        return "Invalid priority. Use NORMAL, HIGH, or CRITICAL."

    async with async_session() as db:
        result = await db.execute(
            select(Appointment, Patient)
            .join(Patient, Appointment.patient_id == Patient.id)
            .where(Patient.uhid == patient_uhid, Appointment.status.in_(["booked", "checked_in"]))
        )
        row = result.first()
        if not row:
            return f"No active appointment found for {patient_uhid}."

        appt, patient = row
        appt.priority = priority
        await log_action(db, patient.user_id, "SET_PRIORITY", "appointment", appt.id,
                        {"uhid": patient_uhid, "priority": priority})
        await db.commit()

    return f"Priority for {patient_uhid} set to {priority}."


@tool
async def get_audit_log(limit: int = 20) -> str:
    """Get recent audit log entries. Shows last N actions (default 20)."""
    async with async_session() as db:
        result = await db.execute(
            select(AuditLog, User)
            .join(User, AuditLog.user_id == User.id)
            .order_by(AuditLog.created_at.desc())
            .limit(limit)
        )
        rows = result.all()

    if not rows:
        return "No audit log entries."

    output = "Recent Audit Log:\n"
    for log, user in rows:
        details_str = str(log.details) if log.details else ""
        output += f"  [{log.created_at.strftime('%Y-%m-%d %H:%M')}] {user.full_name} — {log.action} {log.target_type or ''} {details_str}\n"
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
