"""
Auto-generate consultation reports using LLM, create PDF, upload to Google Drive, email to patient.
"""
import os
import uuid
from datetime import datetime
from fpdf import FPDF
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
REPORTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "reports")
os.makedirs(REPORTS_DIR, exist_ok=True)


def generate_report_content(patient_name: str, patient_uhid: str, patient_gender: str,
                            patient_blood_group: str, patient_age: str,
                            doctor_name: str, specialization: str,
                            appointment_date: str, appointment_time: str,
                            doctor_notes: str = "") -> str:
    """Use LLM to auto-generate a consultation report."""
    prompt = f"""Generate a professional medical consultation report.

Patient: {patient_name} (UHID: {patient_uhid})
Gender: {patient_gender} | Blood Group: {patient_blood_group} | Age: {patient_age}
Doctor: {doctor_name} ({specialization})
Date: {appointment_date} | Time: {appointment_time}
Doctor's Notes: {doctor_notes if doctor_notes else "General consultation - routine checkup"}

Generate a structured report with:
1. PATIENT INFORMATION
2. CONSULTATION DETAILS
3. OBSERVATIONS & DIAGNOSIS
4. PRESCRIPTION & RECOMMENDATIONS
5. FOLLOW-UP ADVICE

Keep it professional. Do not add disclaimers."""

    response = client.chat.completions.create(
        model=os.getenv("LLM_MODEL", "gpt-4o-mini"),
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1000,
    )
    return response.choices[0].message.content


def generate_pdf(report_content: str, patient_name: str, patient_uhid: str,
                 doctor_name: str, appointment_date: str) -> str:
    """Generate a PDF from the report. Returns file path."""
    pdf = FPDF()
    pdf.add_page()

    # Header
    pdf.set_font("Helvetica", "B", 16)
    pdf.cell(0, 10, "HMS - Consultation Report", ln=True, align="C")
    pdf.set_font("Helvetica", "", 10)
    pdf.cell(0, 6, f"Date: {appointment_date}", ln=True, align="C")
    pdf.ln(5)
    pdf.set_draw_color(0, 102, 204)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)

    # Clean markdown and special chars
    import re
    clean = report_content.replace("**", "").replace("##", "").replace("###", "").replace("#", "")
    clean = clean.replace("\u2013", "-").replace("\u2014", "-").replace("\u2018", "'").replace("\u2019", "'")
    clean = clean.replace("\u201c", '"').replace("\u201d", '"')
    clean = re.sub(r'[^\x00-\x7F]+', '', clean)  # Remove non-ASCII

    pdf.set_font("Helvetica", "", 11)
    for line in clean.split("\n"):
        line = line.strip()
        if not line:
            pdf.ln(3)
            continue
        try:
            if any(line.startswith(f"{i}.") for i in range(1, 6)) or (line.isupper() and len(line) > 3):
                pdf.set_font("Helvetica", "B", 12)
                pdf.multi_cell(190, 8, line)
                pdf.set_font("Helvetica", "", 11)
            elif line.startswith("- "):
                pdf.multi_cell(190, 6, "  " + line)
            else:
                pdf.multi_cell(190, 6, line)
        except Exception:
            pass  # Skip problematic lines

    # Footer
    pdf.ln(10)
    pdf.set_draw_color(0, 102, 204)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    pdf.set_font("Helvetica", "I", 9)
    pdf.cell(0, 5, f"Patient: {patient_name} ({patient_uhid}) | Doctor: {doctor_name}", ln=True)
    pdf.cell(0, 5, f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}", ln=True)

    filename = f"report_{patient_uhid}_{appointment_date}_{uuid.uuid4().hex[:6]}.pdf"
    filepath = os.path.join(REPORTS_DIR, filename)
    pdf.output(filepath)
    return filepath


def upload_to_drive(filepath: str, patient_email: str) -> str:
    """Upload PDF to Google Drive and share with patient. Returns shareable link."""
    try:
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload
        import requests as http_requests

        client_id = os.getenv("GOOGLE_CLIENT_ID")
        client_secret = os.getenv("GOOGLE_CLIENT_SECRET")

        # Use a stored refresh token for Drive access
        refresh_token = os.getenv("GOOGLE_DRIVE_REFRESH_TOKEN", "")
        if not refresh_token:
            print(f"[DRIVE] No refresh token. PDF saved locally: {filepath}")
            return ""

        # Get access token from refresh token
        token_r = http_requests.post("https://oauth2.googleapis.com/token", data={
            "client_id": client_id,
            "client_secret": client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        })
        if token_r.status_code != 200:
            print(f"[DRIVE] Token refresh failed. PDF saved locally: {filepath}")
            return ""

        access_token = token_r.json()["access_token"]
        creds = Credentials(token=access_token)
        service = build("drive", "v3", credentials=creds)

        # Upload file
        file_metadata = {"name": os.path.basename(filepath)}
        media = MediaFileUpload(filepath, mimetype="application/pdf")
        file = service.files().create(body=file_metadata, media_body=media, fields="id,webViewLink").execute()

        # Share with patient
        service.permissions().create(
            fileId=file["id"],
            body={"type": "anyone", "role": "reader"},
        ).execute()

        link = file.get("webViewLink", "")
        print(f"[DRIVE] Uploaded: {link}")
        return link
    except Exception as e:
        print(f"[DRIVE] Upload failed: {e}. PDF saved locally: {filepath}")
        return ""


async def send_report_email(email: str, patient_name: str, doctor_name: str,
                            pdf_path: str, drive_link: str = ""):
    """Send report to patient via email with Drive link and/or PDF attachment."""
    import smtplib
    from email.mime.multipart import MIMEMultipart
    from email.mime.text import MIMEText
    from email.mime.base import MIMEBase
    from email import encoders

    try:
        host = os.getenv("SMTP_HOST")
        port = int(os.getenv("SMTP_PORT", "587"))
        user = os.getenv("SMTP_USER")
        pwd = os.getenv("SMTP_PASSWORD")
        if not all([host, user, pwd]):
            print(f"[REPORT] Email not configured. PDF: {pdf_path}")
            return

        msg = MIMEMultipart()
        msg["Subject"] = f"Consultation Report — {doctor_name} — HMS"
        msg["From"] = user
        msg["To"] = email

        drive_section = ""
        if drive_link:
            drive_section = f'<p><b>View Report:</b> <a href="{drive_link}">{drive_link}</a></p>'

        body = f"""<p>Hi {patient_name},</p>
        <p>Your consultation report from <b>{doctor_name}</b> is ready.</p>
        {drive_section}
        <p>The report is also attached as a PDF.</p>
        <p>Take care!</p>
        <p>— HMS Hospital Management System</p>"""
        msg.attach(MIMEText(body, "html"))

        # Attach PDF
        with open(pdf_path, "rb") as f:
            attachment = MIMEBase("application", "pdf")
            attachment.set_payload(f.read())
            encoders.encode_base64(attachment)
            attachment.add_header("Content-Disposition", "attachment",
                                 filename=os.path.basename(pdf_path))
            msg.attach(attachment)

        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, pwd)
            server.send_message(msg)
        print(f"[REPORT] Email sent to {email}")
    except Exception as e:
        print(f"[REPORT] Email failed: {e}")
