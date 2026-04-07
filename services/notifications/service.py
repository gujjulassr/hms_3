"""
Notification service — sends email notifications for key events.
All functions are async and safe to call (they catch errors silently).
"""
import os
import smtplib
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()


def _send_email(to_email: str, subject: str, body: str):
    """Send email via SMTP. Fails silently if not configured."""
    try:
        host = os.getenv("SMTP_HOST")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER")
        pwd = os.getenv("SMTP_PASSWORD")
        if not all([host, user, pwd]):
            print(f"[NOTIFY] Email not configured. Would send to {to_email}: {subject}")
            return
        msg = MIMEText(body, "html")
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to_email
        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, pwd)
            server.send_message(msg)
        print(f"[NOTIFY] Email sent to {to_email}: {subject}")
    except Exception as e:
        print(f"[NOTIFY] Email failed for {to_email}: {e}")


async def notify_booking(email: str, patient_name: str, doctor_name: str, date: str, time: str, uhid: str):
    _send_email(email, "Appointment Booked",
        f"<p>Hi {patient_name},</p><p>Your appointment with Dr. {doctor_name} is booked for <b>{date}</b> at <b>{time}</b>.</p><p>UHID: {uhid}</p>")


async def notify_cancellation(email: str, patient_name: str, doctor_name: str, date: str, time: str):
    _send_email(email, "Appointment Cancelled",
        f"<p>Hi {patient_name},</p><p>Your appointment with Dr. {doctor_name} on {date} at {time} has been cancelled.</p>")


async def notify_checkin(email: str, patient_name: str, doctor_name: str, wait_minutes: int):
    _send_email(email, "Checked In",
        f"<p>Hi {patient_name},</p><p>You are checked in for Dr. {doctor_name}. Estimated wait: ~{wait_minutes} min.</p>")


async def notify_no_show(email: str, patient_name: str, doctor_name: str, risk_score: int):
    _send_email(email, "Missed Appointment",
        f"<p>Hi {patient_name},</p><p>You missed your appointment with Dr. {doctor_name}. Your risk score is now {risk_score}.</p>")


async def notify_feedback(email: str, patient_name: str, doctor_name: str):
    _send_email(email, "Appointment Complete",
        f"<p>Hi {patient_name},</p><p>Your consultation with Dr. {doctor_name} is complete. Thank you!</p>")


async def notify_session_cancelled(email: str, patient_name: str, doctor_name: str, date: str):
    _send_email(email, "Session Cancelled",
        f"<p>Hi {patient_name},</p><p>Dr. {doctor_name}'s session on {date} has been cancelled. Please rebook.</p>")
