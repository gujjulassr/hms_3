from fastapi import APIRouter, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select
from passlib.context import CryptContext
import uuid
import os
import requests as http_requests

from config.database import AsyncSessionLocal as async_session
from config.auth import create_token
from models.user import User
from models.patient import Patient
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI")


class RegisterRequest(BaseModel):
    email: str
    password: str
    full_name: str
    phone: str = ""
    role: str = "patient"
    # Patient fields
    gender: str = ""
    blood_group: str = ""
    # Doctor fields
    specialization: str = ""


class LoginRequest(BaseModel):
    email: str
    password: str


@router.post("/register")
async def register(req: RegisterRequest):
    async with async_session() as db:
        # Check duplicate
        existing = await db.execute(select(User).where(User.email == req.email))
        if existing.scalars().first():
            raise HTTPException(status_code=400, detail="Email already registered")

        user = User(
            id=uuid.uuid4(),
            email=req.email,
            password_hash=pwd_context.hash(req.password),
            full_name=req.full_name,
            phone=req.phone,
            role=req.role,
            is_active=True
        )
        db.add(user)
        await db.flush()

        if req.role == "patient":
            # Generate UHID
            last = await db.execute(select(Patient).order_by(Patient.uhid.desc()))
            last_patient = last.scalars().first()
            if last_patient:
                last_num = int(last_patient.uhid.split("-")[-1])
                uhid = f"HMS-{datetime.now().year}-{str(last_num + 1).zfill(5)}"
            else:
                uhid = f"HMS-{datetime.now().year}-00001"

            patient = Patient(
                id=uuid.uuid4(),
                user_id=user.id,
                uhid=uhid,
                gender=req.gender,
                blood_group=req.blood_group
            )
            db.add(patient)
            await db.commit()
            return {"message": f"Patient registered. UHID: {uhid}", "uhid": uhid}

        elif req.role == "doctor":
            from models.doctor import Doctor
            doctor = Doctor(
                id=uuid.uuid4(),
                user_id=user.id,
                specialization=req.specialization
            )
            db.add(doctor)
            await db.commit()
            return {"message": f"Doctor registered: {req.full_name}"}

        else:
            await db.commit()
            return {"message": f"User registered as {req.role}"}


@router.post("/login")
async def login(req: LoginRequest):
    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == req.email))
        user = result.scalars().first()
        if not user or not pwd_context.verify(req.password, user.password_hash):
            raise HTTPException(status_code=401, detail="Invalid credentials")

        token = create_token({"email": user.email, "role": user.role, "name": user.full_name})
        return {"token": token, "role": user.role, "name": user.full_name}


# ─── Google Form Registration + Auto-Booking ─────────────────────────────

class GoogleFormRequest(BaseModel):
    full_name: str
    email: str
    phone: str
    preferred_date: str          # YYYY-MM-DD
    preferred_time: str          # HH:MM
    reason: str = ""             # e.g. "Eye Examination"
    doctor_name: str             # e.g. "Dr. Anderson"
    gender: str = ""
    blood_group: str = ""
    date_of_birth: str = ""
    address: str = ""
    emergency_contact_name: str = ""
    emergency_contact_phone: str = ""
    api_key: str = ""


@router.post("/google-form-register")
async def google_form_register(req: GoogleFormRequest):
    """
    Full pipeline: Google Form → Register patient → Validate → Book appointment → Email confirmation.
    Secured by API key.
    """
    from models.doctor import Doctor
    from models.session import Session as SessionModel
    from models.appointment import Appointment
    from tools.appointment_tools import find_free_slot
    from services.notifications.service import notify_booking
    from utils.validators import validate_email, validate_phone

    expected_key = os.getenv("PUBLIC_REGISTER_KEY", "hms-register-2026")
    if req.api_key != expected_key:
        raise HTTPException(status_code=401, detail="Invalid API key.")

    # ── LO1: Extract (already done by form) ──

    # ── LO2: Transform & Validate ──
    if not validate_email(req.email):
        raise HTTPException(status_code=400, detail=f"Invalid email: {req.email}")
    if req.phone and not validate_phone(req.phone):
        raise HTTPException(status_code=400, detail=f"Invalid phone: {req.phone}")

    # Parse date — handle multiple formats
    try:
        appt_date = datetime.strptime(req.preferred_date.strip(), "%Y-%m-%d").date()
    except ValueError:
        try:
            appt_date = datetime.strptime(req.preferred_date.strip(), "%m/%d/%Y").date()
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid date. Use YYYY-MM-DD.")

    # Parse time — handle all common formats
    raw_time = req.preferred_time.strip().upper().replace(" ", "")
    appt_time = None
    for fmt in ["%I:%M%p", "%I%p", "%H:%M", "%H:%M:%S", "%I:%M %p"]:
        try:
            parsed = datetime.strptime(raw_time, fmt)
            appt_time = parsed.strftime("%H:%M")
            break
        except ValueError:
            continue
    if not appt_time:
        raise HTTPException(status_code=400, detail=f"Invalid time format: {req.preferred_time}. Use HH:MM.")

    async with async_session() as db:
        # T4: Lookup doctor
        doc_search = req.doctor_name.replace("Dr.", "").replace("dr.", "").strip()
        doc_r = await db.execute(
            select(Doctor, User).join(User, Doctor.user_id == User.id)
            .where(User.full_name.ilike(f"%{doc_search}%"))
        )
        doc_row = doc_r.first()
        if not doc_row:
            raise HTTPException(status_code=404, detail=f"Doctor '{req.doctor_name}' not found.")
        doctor, doc_user = doc_row

        # T5: Check availability — find session
        sess_r = await db.execute(
            select(SessionModel).where(
                SessionModel.doctor_id == doctor.id,
                SessionModel.session_date == appt_date,
                SessionModel.status.in_(["scheduled", "active"])
            )
        )
        session = sess_r.scalars().first()
        if not session:
            raise HTTPException(status_code=404, detail=f"No session for {doc_user.full_name} on {appt_date}.")

        # Check if requested slot is full
        from sqlalchemy import func as sqlfunc
        from services.slot_utils import generate_slot_times
        requested_time = datetime.strptime(appt_time, "%H:%M").time()
        all_slots = generate_slot_times(
            session.start_time, session.end_time, session.slot_duration_minutes,
            session.lunch_start, session.lunch_end, session.overtime_minutes
        )
        target_slot = next((s for s in all_slots if s["slot_time"] == requested_time), None)
        if target_slot:
            from sqlalchemy import select as sa_select
            count_r = await db.execute(
                sa_select(sqlfunc.count(Appointment.id)).where(
                    Appointment.session_id == session.id,
                    Appointment.slot_number == target_slot["slot_number"],
                    Appointment.status.in_(["booked", "checked_in", "in_progress"])
                )
            )
            count = count_r.scalar() or 0
            if count >= session.max_per_slot:
                next_slot = await find_free_slot(db, session, appt_time)
                if next_slot:
                    _, _, next_time = next_slot
                    raise HTTPException(status_code=409,
                        detail=f"Slot at {appt_time} is full. Next available: {next_time} on {appt_date}.")
                else:
                    raise HTTPException(status_code=409,
                        detail=f"No available slots on {appt_date} for {doc_user.full_name}.")

        # Find free slot
        slot_result = await find_free_slot(db, session, appt_time)
        if not slot_result:
            raise HTTPException(status_code=409, detail=f"No available slots on {appt_date}.")
        slot_number, position, slot_time = slot_result

        # ── LO3: Register or find patient ──
        existing_user = await db.execute(select(User).where(User.email == req.email))
        user = existing_user.scalars().first()

        if not user:
            # New patient — register
            user = User(
                id=uuid.uuid4(),
                email=req.email,
                password_hash=pwd_context.hash("password123"),
                full_name=req.full_name,
                phone=req.phone,
                role="patient",
                is_active=True
            )
            db.add(user)
            await db.flush()

            # Generate UHID
            last = await db.execute(select(Patient).order_by(Patient.uhid.desc()))
            last_patient = last.scalars().first()
            if last_patient:
                last_num = int(last_patient.uhid.split("-")[-1])
                uhid = f"HMS-{datetime.now().year}-{str(last_num + 1).zfill(5)}"
            else:
                uhid = f"HMS-{datetime.now().year}-00001"

            dob = None
            if req.date_of_birth:
                try:
                    dob = datetime.strptime(req.date_of_birth, "%Y-%m-%d").date()
                except ValueError:
                    pass

            patient = Patient(
                id=uuid.uuid4(),
                user_id=user.id,
                uhid=uhid,
                gender=req.gender,
                blood_group=req.blood_group,
                date_of_birth=dob,
                address=req.address,
                emergency_contact_name=req.emergency_contact_name,
                emergency_contact_phone=req.emergency_contact_phone
            )
            db.add(patient)
            await db.flush()
            registered = True
        else:
            # Existing patient
            pat_r = await db.execute(select(Patient).where(Patient.user_id == user.id))
            patient = pat_r.scalars().first()
            if not patient:
                raise HTTPException(status_code=400, detail="User exists but has no patient profile.")
            uhid = patient.uhid
            registered = False

        # Check duplicate booking
        dup_r = await db.execute(
            select(Appointment).where(
                Appointment.session_id == session.id,
                Appointment.patient_id == patient.id,
                Appointment.status.in_(["booked", "checked_in", "in_progress"])
            )
        )
        if dup_r.scalars().first():
            raise HTTPException(status_code=409, detail=f"Patient {uhid} already has an appointment in this session.")

        # ── Create appointment ──
        new_appt = Appointment(
            id=uuid.uuid4(),
            session_id=session.id,
            patient_id=patient.id,
            booked_by=user.id,
            slot_number=slot_number,
            slot_position=position,
            slot_time=slot_time,
            status="booked",
            notes=req.reason
        )
        db.add(new_appt)
        await db.commit()

    # ── Send confirmation email with calendar invite ──
    await notify_booking(req.email, req.full_name, doc_user.full_name,
                         str(appt_date), str(slot_time), uhid)

    return {
        "status": "success",
        "registered": registered,
        "uhid": uhid,
        "appointment": {
            "doctor": doc_user.full_name,
            "date": str(appt_date),
            "time": str(slot_time),
            "slot_number": slot_number,
            "reason": req.reason,
        },
        "message": f"{'Registered and booked' if registered else 'Booked'}: {req.full_name} with {doc_user.full_name} on {appt_date} at {slot_time}."
    }


# ─── Change Password ──────────────────────────────────────────────────────

class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


@router.post("/change-password/{email}")
async def change_password_by_email(email: str, req: ChangePasswordRequest):
    """Change password for a user by email."""
    async with async_session() as db:
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalars().first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found.")
        if not pwd_context.verify(req.current_password, user.password_hash):
            raise HTTPException(status_code=401, detail="Current password is incorrect.")
        if len(req.new_password) < 6:
            raise HTTPException(status_code=400, detail="New password must be at least 6 characters.")
        user.password_hash = pwd_context.hash(req.new_password)
        await db.commit()
    return {"message": "Password changed successfully."}


# ─── Google OAuth ──────────────────────────────────────────────────────────

@router.get("/google/login")
async def google_login():
    """Redirect to Google OAuth consent screen."""
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={GOOGLE_REDIRECT_URI}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile%20https://www.googleapis.com/auth/drive.file"
        f"&access_type=offline"
        f"&prompt=consent"
    )
    return {"auth_url": google_auth_url}


@router.get("/google/callback")
async def google_callback(code: str):
    """Handle Google OAuth callback — exchange code for token, create/login user."""
    # Exchange code for tokens
    token_response = http_requests.post(
        "https://oauth2.googleapis.com/token",
        data={
            "code": code,
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "grant_type": "authorization_code",
        }
    )
    if token_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Google auth failed")

    token_data = token_response.json()
    access_token = token_data.get("access_token")
    refresh_token = token_data.get("refresh_token")

    # Save refresh token for Google Drive access
    if refresh_token:
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
        try:
            with open(env_path, "r") as f:
                env_content = f.read()
            if "GOOGLE_DRIVE_REFRESH_TOKEN=" in env_content:
                import re
                env_content = re.sub(r'GOOGLE_DRIVE_REFRESH_TOKEN=.*', f'GOOGLE_DRIVE_REFRESH_TOKEN={refresh_token}', env_content)
            else:
                env_content += f"\nGOOGLE_DRIVE_REFRESH_TOKEN={refresh_token}\n"
            with open(env_path, "w") as f:
                f.write(env_content)
            os.environ["GOOGLE_DRIVE_REFRESH_TOKEN"] = refresh_token
            print(f"[GOOGLE] Refresh token saved for Drive access")
        except Exception as e:
            print(f"[GOOGLE] Could not save refresh token: {e}")

    # Get user info from Google
    user_info = http_requests.get(
        "https://www.googleapis.com/oauth2/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    ).json()

    google_email = user_info.get("email")
    google_name = user_info.get("name", google_email.split("@")[0])

    if not google_email:
        raise HTTPException(status_code=400, detail="Could not get email from Google")

    async with async_session() as db:
        # Check if user exists
        result = await db.execute(select(User).where(User.email == google_email))
        user = result.scalars().first()

        if not user:
            # Auto-register as patient
            user = User(
                id=uuid.uuid4(),
                email=google_email,
                password_hash=pwd_context.hash(str(uuid.uuid4())),  # Random password (won't be used)
                full_name=google_name,
                phone="",
                role="patient",
                is_active=True
            )
            db.add(user)
            await db.flush()

            # Generate UHID
            last = await db.execute(select(Patient).order_by(Patient.uhid.desc()))
            last_patient = last.scalars().first()
            if last_patient:
                last_num = int(last_patient.uhid.split("-")[-1])
                uhid = f"HMS-{datetime.now().year}-{str(last_num + 1).zfill(5)}"
            else:
                uhid = f"HMS-{datetime.now().year}-00001"

            patient = Patient(
                id=uuid.uuid4(),
                user_id=user.id,
                uhid=uhid,
                gender="",
                blood_group=""
            )
            db.add(patient)
            await db.commit()

        # Create JWT token
        jwt_token = create_token({"email": user.email, "role": user.role, "name": user.full_name})

    # Redirect to Streamlit with token
    streamlit_port = os.getenv("STREAMLIT_PORT", "8501")
    return RedirectResponse(
        f"http://localhost:{streamlit_port}?token={jwt_token}&role={user.role}&name={user.full_name}"
    )
