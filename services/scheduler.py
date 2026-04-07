"""
Background scheduler — runs every 2 minutes.
Auto-completes sessions that have passed their end_time + overtime.
  - booked → no_show (risk +20)
  - checked_in → cancelled (no risk penalty)
"""
import asyncio
from datetime import datetime, date, timedelta
from sqlalchemy import select
from config.database import AsyncSessionLocal as async_session
from models.session import Session
from models.appointment import Appointment
from models.patient import Patient
from models.doctor import Doctor
from models.user import User


async def auto_complete_expired_sessions():
    """Find active sessions past their end time and auto-complete them."""
    async with async_session() as db:
        now = datetime.now().time()

        # Find active sessions where (end_time + overtime) has passed
        result = await db.execute(
            select(Session).where(
                Session.session_date == date.today(),
                Session.status == "active"
            )
        )
        sessions = result.scalars().all()

        for session in sessions:
            # Calculate actual end time including overtime
            actual_end = (datetime.combine(date.today(), session.end_time) +
                         timedelta(minutes=session.overtime_minutes)).time()

            if now <= actual_end:
                continue  # Session still running

            print(f"[SCHEDULER] Auto-completing session {session.id} (ended at {actual_end})")

            # Get doctor info for notifications
            doc_result = await db.execute(
                select(Doctor, User).join(User, Doctor.user_id == User.id)
                .where(Doctor.id == session.doctor_id)
            )
            doc_row = doc_result.first()
            doc_user = doc_row[1] if doc_row else None

            # Get pending appointments
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
                    # Never checked in → no_show
                    appt.status = "no_show"
                    patient.risk_score = (patient.risk_score or 0) + 20
                    no_show_count += 1
                    # Send notification
                    pat_user_r = await db.execute(select(User).where(User.id == patient.user_id))
                    pat_user = pat_user_r.scalars().first()
                    if pat_user and doc_user:
                        await notify_no_show(pat_user.email, pat_user.full_name,
                                           doc_user.full_name, patient.risk_score)

                elif appt.status == "checked_in":
                    # Was checked in but not seen → cancelled (NO risk penalty)
                    appt.status = "cancelled"
                    cancelled_count += 1

            session.status = "completed"
            await db.commit()

            print(f"[SCHEDULER] Session {session.id} completed: {no_show_count} no-shows, {cancelled_count} cancelled")


async def scheduler_loop():
    """Run the scheduler every 2 minutes."""
    print("[SCHEDULER] Background scheduler started (interval: 120s)")
    while True:
        try:
            await auto_complete_expired_sessions()
        except Exception as e:
            print(f"[SCHEDULER] Error: {e}")
        await asyncio.sleep(120)
