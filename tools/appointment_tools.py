from langchain_core.tools import tool
from sqlalchemy import select, func
from models.session import Session
from models.appointment import Appointment
from models.patient import Patient
from models.doctor import Doctor
from models.user import User
from config.database import AsyncSessionLocal as async_session
import uuid
from datetime import datetime, timedelta, date, time
from services.audit import log_action
from services.notifications.service import notify_booking, notify_cancellation
from services.slot_utils import generate_slot_times, is_lunch_time


async def find_free_slot(db, session, preferred_time=""):
    """
    Find first available slot in a session, skipping lunch break.
    Returns (slot_number, position, slot_time) or None.
    """
    # Generate all valid slots (lunch excluded)
    all_slots = generate_slot_times(
        session.start_time, session.end_time, session.slot_duration_minutes,
        session.lunch_start, session.lunch_end, session.overtime_minutes
    )

    # Get occupied slot counts
    slot_counts = await db.execute(
        select(Appointment.slot_number, func.count(Appointment.id).label("count")).where(
            Appointment.session_id == session.id,
            Appointment.status.in_(["booked", "checked_in", "in_progress"])
        ).group_by(Appointment.slot_number)
    )
    occupied = {row.slot_number: row.count for row in slot_counts}

    # Calculate min slot (skip past slots if today)
    min_slot = 1
    if session.session_date == date.today():
        now = datetime.now()
        start = datetime.combine(session.session_date, session.start_time)
        diff = (now - start).total_seconds() / 60
        if diff > 0:
            min_slot = int(diff // session.slot_duration_minutes) + 2

    # If preferred time given, validate it's in session range and not in lunch
    target_slot = None
    if preferred_time:
        pref = datetime.strptime(preferred_time, "%H:%M").time()

        # Check if preferred time is in lunch break
        if is_lunch_time(pref, session.lunch_start, session.lunch_end):
            return None  # Can't book during lunch

        # Check if preferred time is within session range
        actual_end = (datetime.combine(session.session_date, session.end_time) +
                     timedelta(minutes=session.overtime_minutes)).time()
        if pref < session.start_time or pref >= actual_end:
            return None  # Outside session range

        # Find the slot that matches or is closest to preferred time
        for slot in all_slots:
            if slot["slot_time"] >= pref and slot["slot_number"] >= min_slot:
                target_slot = slot["slot_number"]
                break

    # Search for free slot starting from target or min
    start_from = target_slot if target_slot else min_slot
    for slot in all_slots:
        if slot["slot_number"] < start_from:
            continue
        count = occupied.get(slot["slot_number"], 0)
        if count < session.max_per_slot:
            return slot["slot_number"], count + 1, slot["slot_time"]

    return None


@tool
async def book_appointment(patient_uhid: str, doctor_name: str, preferred_time: str = "", confirm: bool = False) -> str:
    """Book an appointment for a patient with a doctor. Provide patient UHID, doctor name, and optionally preferred time like '09:15'.
    Set confirm=True only after patient confirms the slot."""
    async with async_session() as db:
        # Validate time format
        if preferred_time:
            try:
                datetime.strptime(preferred_time, "%H:%M").time()
            except ValueError:
                return "Invalid time format. Use HH:MM like '09:15'."

        # Find patient
        patient_result = await db.execute(select(Patient).where(Patient.uhid == patient_uhid))
        patient = patient_result.scalars().first()
        if not patient:
            return f"Patient {patient_uhid} not found."

        # Find doctor
        doctor_result = await db.execute(
            select(Doctor, User).join(User, Doctor.user_id == User.id)
            .where(User.full_name.ilike(f"%{doctor_name}%"))
        )
        doctor_row = doctor_result.first()
        if not doctor_row:
            return f"Doctor {doctor_name} not found."
        doctor, doc_user = doctor_row

        # Find available sessions (one per day, but check today + future)
        session_result = await db.execute(
            select(Session).where(
                Session.doctor_id == doctor.id,
                Session.status.in_(["scheduled", "active"]),
                Session.session_date >= date.today()
            ).order_by(Session.session_date, Session.start_time)
        )
        all_sessions = session_result.scalars().all()
        if not all_sessions:
            return f"No available sessions for Dr. {doc_user.full_name}."

        # Try each session
        found_slot = None
        found_position = None
        slot_time = None
        chosen_session = None

        for s in all_sessions:
            # Skip sessions that have already ended today
            actual_end = (datetime.combine(s.session_date, s.end_time) +
                         timedelta(minutes=s.overtime_minutes)).time() if s.overtime_minutes > 0 else s.end_time
            if s.session_date == date.today() and actual_end <= datetime.now().time():
                continue

            result = await find_free_slot(db, s, preferred_time)
            if result:
                found_slot, found_position, slot_time = result
                chosen_session = s
                # Different slot than requested — ask confirmation
                if preferred_time and str(slot_time) != preferred_time + ":00" and not confirm:
                    return f"Slot at {preferred_time} is full. Nearest available is {slot_time} on {s.session_date}. Reply 'yes' to book at {slot_time}."
                break

        if not found_slot:
            return f"No available slots for Dr. {doc_user.full_name} in any session."

        # Ask confirmation before booking
        if not confirm:
            return f"Found slot: Doctor: {doc_user.full_name}, Date: {chosen_session.session_date}, Time: {slot_time}, Slot: {found_slot}. Say 'yes' to confirm booking."

        # Check duplicate booking
        existing = await db.execute(
            select(Appointment).where(
                Appointment.session_id == chosen_session.id,
                Appointment.patient_id == patient.id,
                Appointment.status.in_(["booked", "checked_in", "in_progress"])
            )
        )
        if existing.scalars().first():
            return f"Patient {patient_uhid} already has an appointment in this session."

        # Create appointment
        new_appt = Appointment(
            id=uuid.uuid4(),
            session_id=chosen_session.id,
            patient_id=patient.id,
            booked_by=patient.user_id,
            slot_number=found_slot,
            slot_position=found_position,
            slot_time=slot_time,
            status="booked"
        )
        db.add(new_appt)
        await log_action(db, patient.user_id, "BOOK", "appointment", new_appt.id,
                        {"uhid": patient_uhid, "doctor": doc_user.full_name, "slot": found_slot, "time": str(slot_time)})

        pat_user_r = await db.execute(select(User).where(User.id == patient.user_id))
        pat_user = pat_user_r.scalars().first()
        await db.commit()

    if pat_user:
        await notify_booking(pat_user.email, pat_user.full_name, doc_user.full_name,
                           str(chosen_session.session_date), str(slot_time), patient_uhid)

    return f"Appointment booked! Patient: {patient_uhid}, Doctor: {doc_user.full_name}, Date: {chosen_session.session_date}, Time: {slot_time}, Slot: {found_slot}"


@tool
async def check_earliest_slot(doctor_name: str) -> str:
    """Check the earliest available slot for a doctor without booking."""
    async with async_session() as db:
        doctor_result = await db.execute(
            select(Doctor, User).join(User, Doctor.user_id == User.id)
            .where(User.full_name.ilike(f"%{doctor_name}%"))
        )
        doctor_row = doctor_result.first()
        if not doctor_row:
            return f"Doctor {doctor_name} not found."
        doctor, doc_user = doctor_row

        session_result = await db.execute(
            select(Session).where(
                Session.doctor_id == doctor.id,
                Session.status.in_(["scheduled", "active"]),
                Session.session_date >= date.today()
            ).order_by(Session.session_date, Session.start_time)
        )
        all_sessions = session_result.scalars().all()
        if not all_sessions:
            return f"No available sessions for Dr. {doc_user.full_name}."

        for s in all_sessions:
            if s.session_date == date.today() and s.end_time <= datetime.now().time():
                continue
            result = await find_free_slot(db, s)
            if result:
                slot_num, position, slot_time = result
                return f"Earliest slot for Dr. {doc_user.full_name}: {s.session_date} at {slot_time} (Slot {slot_num}). Say 'book' to confirm."

    return f"No available slots for Dr. {doc_user.full_name}."


@tool
async def get_my_appointments(patient_uhid: str) -> str:
    """Get all appointments for a patient by their UHID."""
    async with async_session() as db:
        result = await db.execute(
            select(Appointment, Session, Doctor, User)
            .join(Session, Appointment.session_id == Session.id)
            .join(Doctor, Session.doctor_id == Doctor.id)
            .join(User, Doctor.user_id == User.id)
            .where(
                Appointment.patient_id.in_(
                    select(Patient.id).where(Patient.uhid == patient_uhid)
                )
            ).order_by(Session.session_date.desc(), Appointment.slot_time.desc())
        )
        rows = result.all()

    if not rows:
        return "No appointments found."

    output = ""
    for appt, session, doctor, user in rows:
        output += f"Doctor: {user.full_name}, Date: {session.session_date}, Time: {appt.slot_time}, Status: {appt.status}, Slot: {appt.slot_number}\n"
    return output


@tool
async def cancel_appointment(patient_uhid: str, doctor_name: str) -> str:
    """Cancel a patient's booked appointment with a doctor."""
    async with async_session() as db:
        result = await db.execute(
            select(Appointment, Patient, Session, Doctor, User)
            .join(Patient, Appointment.patient_id == Patient.id)
            .join(Session, Appointment.session_id == Session.id)
            .join(Doctor, Session.doctor_id == Doctor.id)
            .join(User, Doctor.user_id == User.id)
            .where(
                Patient.uhid == patient_uhid,
                User.full_name.ilike(f"%{doctor_name}%"),
                Appointment.status.in_(["booked", "checked_in"]),
                Session.session_date >= date.today()
            ).order_by(Session.session_date, Appointment.slot_time)
        )
        rows = result.all()

        if not rows:
            return "No booked appointment found to cancel."

        appt, patient, session, doctor, doc_user = None, None, None, None, None
        for row in rows:
            r_appt, r_patient, r_session, r_doctor, r_doc_user = row
            if r_session.status in ["active", "scheduled"]:
                appt, patient, session, doctor, doc_user = r_appt, r_patient, r_session, r_doctor, r_doc_user
                break

        if not appt:
            return "All booked appointments have already passed."

        appt.status = "cancelled"
        patient.risk_score = (patient.risk_score or 0) + 10
        await log_action(db, patient.user_id, "CANCEL", "appointment", appt.id,
                        {"uhid": patient_uhid, "doctor": doc_user.full_name})

        pat_user_r = await db.execute(select(User).where(User.id == patient.user_id))
        pat_user = pat_user_r.scalars().first()
        await db.commit()

    if pat_user:
        await notify_cancellation(pat_user.email, pat_user.full_name, doc_user.full_name,
                                 str(session.session_date), str(appt.slot_time))

    return f"Appointment cancelled for {patient_uhid} with Dr. {doc_user.full_name} on {session.session_date} at {appt.slot_time}. Risk score +10."


@tool
async def reschedule_appointment(patient_uhid: str, doctor_name: str, new_date: str = "", new_time: str = "", confirm: bool = False) -> str:
    """Reschedule a patient's appointment to a new date/time. No risk penalty.
    Provide patient UHID, doctor name, new_date (YYYY-MM-DD), new_time (HH:MM optional).
    Set confirm=True only after patient confirms."""
    async with async_session() as db:
        # Find existing appointment
        result = await db.execute(
            select(Appointment, Patient, Session, Doctor, User)
            .join(Patient, Appointment.patient_id == Patient.id)
            .join(Session, Appointment.session_id == Session.id)
            .join(Doctor, Session.doctor_id == Doctor.id)
            .join(User, Doctor.user_id == User.id)
            .where(
                Patient.uhid == patient_uhid,
                User.full_name.ilike(f"%{doctor_name}%"),
                Appointment.status.in_(["booked", "checked_in"]),
                Session.session_date >= date.today()
            ).order_by(Session.session_date, Appointment.slot_time)
        )
        rows = result.all()
        if not rows:
            return f"No active appointment found for {patient_uhid} with {doctor_name}."

        old_appt, patient, old_session, doctor, doc_user = None, None, None, None, None
        for row in rows:
            r_appt, r_patient, r_session, r_doctor, r_doc_user = row
            if r_session.status in ["active", "scheduled"]:
                old_appt, patient, old_session, doctor, doc_user = r_appt, r_patient, r_session, r_doctor, r_doc_user
                break

        if not old_appt:
            return "No reschedulable appointment found."

        # Parse new date
        target_date = date.today()
        if new_date:
            try:
                target_date = datetime.strptime(new_date, "%Y-%m-%d").date()
            except ValueError:
                return "Invalid date format. Use YYYY-MM-DD."

        # Find session on new date
        sess_r = await db.execute(
            select(Session).where(
                Session.doctor_id == doctor.id,
                Session.session_date == target_date,
                Session.status.in_(["scheduled", "active"])
            )
        )
        new_session = sess_r.scalars().first()
        if not new_session:
            return f"No session for Dr. {doc_user.full_name} on {target_date}."

        # Check if specific requested slot is available
        if new_time:
            from sqlalchemy import func as sqlfunc
            # Check if requested time slot is full
            requested_time = datetime.strptime(new_time, "%H:%M").time()
            all_slots = generate_slot_times(
                new_session.start_time, new_session.end_time, new_session.slot_duration_minutes,
                new_session.lunch_start, new_session.lunch_end, new_session.overtime_minutes
            )
            target_slot = None
            for s in all_slots:
                if s["slot_time"] == requested_time:
                    target_slot = s
                    break
            if not target_slot:
                # Time doesn't match any slot, find nearest
                target_slot = next((s for s in all_slots if s["slot_time"] >= requested_time), None)

            if target_slot:
                booked_count = await db.execute(
                    select(sqlfunc.count(Appointment.id)).where(
                        Appointment.session_id == new_session.id,
                        Appointment.slot_number == target_slot["slot_number"],
                        Appointment.status.in_(["booked", "checked_in", "in_progress"])
                    )
                )
                count = booked_count.scalar() or 0
                if count >= new_session.max_per_slot:
                    # Requested slot is full — find next available
                    next_slot = await find_free_slot(db, new_session, new_time)
                    if next_slot:
                        _, _, next_time = next_slot
                        return (f"Slot at {new_time} is full on {target_date}. "
                                f"Next available: {next_time}. Would you like to reschedule to {next_time} instead?")
                    else:
                        return f"Slot at {new_time} is full and no other slots available on {target_date}."

        # Find free slot
        new_slot = await find_free_slot(db, new_session, new_time)
        if not new_slot:
            return f"No available slots for Dr. {doc_user.full_name} on {target_date}."

        slot_number, position, slot_time = new_slot

        if not confirm:
            return (f"Reschedule available: Current: {old_session.session_date} at {old_appt.slot_time} → "
                    f"New: {target_date} at {slot_time} with Dr. {doc_user.full_name}. "
                    f"No risk penalty. Say 'yes' to confirm.")

        # Cancel old (no risk penalty)
        old_appt.status = "rescheduled"
        await log_action(db, patient.user_id, "RESCHEDULE", "appointment", old_appt.id,
                         {"uhid": patient_uhid, "doctor": doc_user.full_name,
                          "old_date": str(old_session.session_date), "old_time": str(old_appt.slot_time),
                          "new_date": str(target_date), "new_time": str(slot_time)})

        # Book new
        import uuid as _uuid
        new_appt = Appointment(
            id=_uuid.uuid4(),
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
                                str(target_date), str(slot_time), patient_uhid)

    return (f"Rescheduled! {old_session.session_date} {old_appt.slot_time} → {target_date} {slot_time} "
            f"with Dr. {doc_user.full_name}. No risk penalty.")
