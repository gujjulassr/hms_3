from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from passlib.context import CryptContext
import uuid

from config.database import AsyncSessionLocal as async_session
from config.auth import create_token
from models.user import User
from models.patient import Patient
from models.doctor import Doctor
from datetime import datetime

router = APIRouter(prefix="/api/auth", tags=["auth"])
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


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
