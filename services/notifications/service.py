"""
Notification service — sends email notifications with calendar invites.
All functions are async and safe to call (they catch errors silently).
"""
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime, timedelta
import uuid
from dotenv import load_dotenv

load_dotenv()


def _generate_ics(summary: str, description: str, date_str: str, time_str: str,
                  duration_minutes: int = 15, location: str = "Hospital", cancelled: bool = False) -> str:
    """Generate an .ics calendar invite string."""
    try:
        # Parse date and time
        dt = datetime.strptime(f"{date_str} {time_str[:5]}", "%Y-%m-%d %H:%M")
        dt_end = dt + timedelta(minutes=duration_minutes)

        # Format for iCal
        dt_start_str = dt.strftime("%Y%m%dT%H%M%S")
        dt_end_str = dt_end.strftime("%Y%m%dT%H%M%S")
        now_str = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
        uid = str(uuid.uuid4())

        status = "CANCELLED" if cancelled else "CONFIRMED"
        method = "CANCEL" if cancelled else "REQUEST"

        ics = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//HMS 3//Hospital Management System//EN
METHOD:{method}
BEGIN:VEVENT
UID:{uid}
DTSTART:{dt_start_str}
DTEND:{dt_end_str}
DTSTAMP:{now_str}
SUMMARY:{summary}
DESCRIPTION:{description}
LOCATION:{location}
STATUS:{status}
END:VEVENT
END:VCALENDAR"""
        return ics
    except Exception:
        return ""


def _send_email(to_email: str, subject: str, body: str, ics_content: str = ""):
    """Send email via SMTP with optional calendar invite. Fails silently if not configured."""
    try:
        host = os.getenv("SMTP_HOST")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER")
        pwd = os.getenv("SMTP_PASSWORD")
        if not all([host, user, pwd]):
            print(f"[NOTIFY] Email not configured. Would send to {to_email}: {subject}")
            return

        if ics_content:
            msg = MIMEMultipart("mixed")
            msg["Subject"] = subject
            msg["From"] = user
            msg["To"] = to_email

            # HTML body
            html_part = MIMEText(body, "html")
            msg.attach(html_part)

            # Calendar invite attachment
            ics_part = MIMEBase("text", "calendar", method="REQUEST")
            ics_part.set_payload(ics_content.encode("utf-8"))
            encoders.encode_base64(ics_part)
            ics_part.add_header("Content-Disposition", "attachment", filename="invite.ics")
            msg.attach(ics_part)
        else:
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
    """Send booking confirmation with calendar invite."""
    ics = _generate_ics(
        summary=f"Appointment with {doctor_name}",
        description=f"Patient: {patient_name} (UHID: {uhid})\nDoctor: {doctor_name}",
        date_str=date, time_str=time
    )
    _send_email(email, "Appointment Booked — HMS",
        f"""<p>Hi {patient_name},</p>
        <p>Your appointment has been booked:</p>
        <table style="border-collapse:collapse;">
        <tr><td style="padding:4px 12px;"><b>Doctor</b></td><td>{doctor_name}</td></tr>
        <tr><td style="padding:4px 12px;"><b>Date</b></td><td>{date}</td></tr>
        <tr><td style="padding:4px 12px;"><b>Time</b></td><td>{time}</td></tr>
        <tr><td style="padding:4px 12px;"><b>UHID</b></td><td>{uhid}</td></tr>
        </table>
        <p>A calendar invite is attached.</p>
        <p>— HMS Hospital Management System</p>""",
        ics_content=ics)


async def notify_cancellation(email: str, patient_name: str, doctor_name: str, date: str, time: str):
    """Send cancellation notification with calendar cancel."""
    ics = _generate_ics(
        summary=f"CANCELLED: Appointment with {doctor_name}",
        description=f"This appointment has been cancelled.",
        date_str=date, time_str=time, cancelled=True
    )
    _send_email(email, "Appointment Cancelled — HMS",
        f"""<p>Hi {patient_name},</p>
        <p>Your appointment has been cancelled:</p>
        <table style="border-collapse:collapse;">
        <tr><td style="padding:4px 12px;"><b>Doctor</b></td><td>{doctor_name}</td></tr>
        <tr><td style="padding:4px 12px;"><b>Date</b></td><td>{date}</td></tr>
        <tr><td style="padding:4px 12px;"><b>Time</b></td><td>{time}</td></tr>
        </table>
        <p>— HMS Hospital Management System</p>""",
        ics_content=ics)


async def notify_reschedule(email: str, patient_name: str, doctor_name: str,
                            old_date: str, old_time: str, new_date: str, new_time: str, uhid: str):
    """Send reschedule notification with new calendar invite."""
    ics = _generate_ics(
        summary=f"Rescheduled: Appointment with {doctor_name}",
        description=f"Patient: {patient_name} (UHID: {uhid})\nDoctor: {doctor_name}\nRescheduled from {old_date} {old_time}",
        date_str=new_date, time_str=new_time
    )
    _send_email(email, "Appointment Rescheduled — HMS",
        f"""<p>Hi {patient_name},</p>
        <p>Your appointment has been rescheduled:</p>
        <table style="border-collapse:collapse;">
        <tr><td style="padding:4px 12px;"><b>Doctor</b></td><td>{doctor_name}</td></tr>
        <tr><td style="padding:4px 12px;"><b>Previous</b></td><td>{old_date} at {old_time}</td></tr>
        <tr><td style="padding:4px 12px;"><b>New</b></td><td>{new_date} at {new_time}</td></tr>
        <tr><td style="padding:4px 12px;"><b>UHID</b></td><td>{uhid}</td></tr>
        </table>
        <p>A new calendar invite is attached.</p>
        <p>— HMS Hospital Management System</p>""",
        ics_content=ics)


async def notify_checkin(email: str, patient_name: str, doctor_name: str, wait_minutes: int):
    _send_email(email, "Checked In — HMS",
        f"""<p>Hi {patient_name},</p>
        <p>You are checked in for <b>{doctor_name}</b>.</p>
        <p>Estimated wait: ~{wait_minutes} minutes.</p>
        <p>— HMS Hospital Management System</p>""")


async def notify_no_show(email: str, patient_name: str, doctor_name: str, risk_score: int):
    _send_email(email, "Missed Appointment — HMS",
        f"""<p>Hi {patient_name},</p>
        <p>You missed your appointment with <b>{doctor_name}</b>.</p>
        <p>Your risk score is now <b>{risk_score}</b>. Repeated no-shows may affect future booking priority.</p>
        <p>— HMS Hospital Management System</p>""")


async def notify_feedback(email: str, patient_name: str, doctor_name: str):
    _send_email(email, "Appointment Complete — HMS",
        f"""<p>Hi {patient_name},</p>
        <p>Your consultation with <b>{doctor_name}</b> is complete. Thank you!</p>
        <p>— HMS Hospital Management System</p>""")


async def notify_session_cancelled(email: str, patient_name: str, doctor_name: str, date: str):
    _send_email(email, "Session Cancelled — HMS",
        f"""<p>Hi {patient_name},</p>
        <p><b>{doctor_name}</b>'s session on <b>{date}</b> has been cancelled.</p>
        <p>Please rebook your appointment.</p>
        <p>— HMS Hospital Management System</p>""")
