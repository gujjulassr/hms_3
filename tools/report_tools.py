from langchain_core.tools import tool
from sqlalchemy import select, func
from models.appointment import Appointment
from models.session import Session
from models.patient import Patient
from models.doctor import Doctor
from models.user import User
from config.database import AsyncSessionLocal as async_session
from datetime import date, timedelta


@tool
async def generate_patient_report(patient_uhid: str) -> str:
    """Generate a summary report for a patient — total visits, no-shows, cancellations, risk score."""
    async with async_session() as db:
        pat_r = await db.execute(
            select(Patient, User).join(User, Patient.user_id == User.id)
            .where(Patient.uhid == patient_uhid)
        )
        row = pat_r.first()
        if not row:
            return f"Patient {patient_uhid} not found."
        patient, user = row

        # Count appointments by status
        counts_r = await db.execute(
            select(Appointment.status, func.count(Appointment.id))
            .where(Appointment.patient_id == patient.id)
            .group_by(Appointment.status)
        )
        counts = {r[0]: r[1] for r in counts_r.all()}

        total = sum(counts.values())
        completed = counts.get("completed", 0)
        cancelled = counts.get("cancelled", 0)
        no_show = counts.get("no_show", 0)
        booked = counts.get("booked", 0)

    return (f"Patient Report — {user.full_name} ({patient_uhid})\n"
            f"Total Appointments: {total}\n"
            f"Completed: {completed}\n"
            f"Cancelled: {cancelled}\n"
            f"No-shows: {no_show}\n"
            f"Upcoming/Booked: {booked}\n"
            f"Risk Score: {patient.risk_score}\n")


@tool
async def generate_session_report(doctor_name: str, report_date: str = "") -> str:
    """Generate a session report for a doctor. Shows patient counts, completion stats, delay info."""
    async with async_session() as db:
        doc_r = await db.execute(
            select(Doctor, User).join(User, Doctor.user_id == User.id)
            .where(User.full_name.ilike(f"%{doctor_name}%"))
        )
        doc_row = doc_r.first()
        if not doc_row:
            return f"Doctor {doctor_name} not found."
        doctor, doc_user = doc_row

        query_date = date.today()
        if report_date:
            try:
                from datetime import datetime
                query_date = datetime.strptime(report_date, "%Y-%m-%d").date()
            except ValueError:
                pass

        sess_r = await db.execute(
            select(Session).where(
                Session.doctor_id == doctor.id,
                Session.session_date == query_date
            )
        )
        sessions = sess_r.scalars().all()

        if not sessions:
            return f"No sessions for Dr. {doc_user.full_name} on {query_date}."

        output = f"Session Report — Dr. {doc_user.full_name} on {query_date}\n\n"
        for s in sessions:
            appt_r = await db.execute(
                select(Appointment.status, func.count(Appointment.id))
                .where(Appointment.session_id == s.id)
                .group_by(Appointment.status)
            )
            counts = {r[0]: r[1] for r in appt_r.all()}
            total = sum(counts.values())

            output += (f"Session: {s.start_time}-{s.end_time} ({s.status.upper()})\n"
                      f"  Total patients: {total}\n"
                      f"  Completed: {counts.get('completed', 0)}\n"
                      f"  No-shows: {counts.get('no_show', 0)}\n"
                      f"  Cancelled: {counts.get('cancelled', 0)}\n"
                      f"  Delay: {s.delay_minutes}min\n"
                      f"  Overtime: {s.overtime_minutes}min\n\n")

    return output
