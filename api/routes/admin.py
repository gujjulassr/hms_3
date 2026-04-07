"""Admin API endpoints — system overview, user management, audit logs."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from datetime import datetime, date, timedelta

from config.database import AsyncSessionLocal as async_session
from config.auth import get_current_user
from models.user import User
from models.patient import Patient
from models.doctor import Doctor
from models.session import Session
from models.appointment import Appointment
from models.audit_log import AuditLog

router = APIRouter(prefix="/api/admin", tags=["admin"])


async def _require_staff(user: dict):
    if user.get("role") not in ["admin", "staff", "nurse"]:
        raise HTTPException(status_code=403, detail="Staff access required.")


async def _require_admin(user: dict):
    if user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")


# ─── Dashboard Stats ───────────────────────────────────────────────────────

@router.get("/stats")
async def get_stats(user: dict = Depends(get_current_user)):
    await _require_staff(user)
    async with async_session() as db:
        total_users = (await db.execute(select(func.count(User.id)))).scalar()
        total_patients = (await db.execute(select(func.count(Patient.id)))).scalar()
        total_doctors = (await db.execute(select(func.count(Doctor.id)))).scalar()
        total_appointments = (await db.execute(select(func.count(Appointment.id)))).scalar()
        today_appointments = (await db.execute(
            select(func.count(Appointment.id))
            .join(Session, Appointment.session_id == Session.id)
            .where(Session.session_date == date.today())
        )).scalar()
        active_sessions = (await db.execute(
            select(func.count(Session.id)).where(Session.status == "active")
        )).scalar()
        total_sessions = (await db.execute(
            select(func.count(Session.id)).where(Session.session_date >= date.today())
        )).scalar()
        no_shows = (await db.execute(
            select(func.count(Appointment.id)).where(Appointment.status == "no_show")
        )).scalar()
        cancellations = (await db.execute(
            select(func.count(Appointment.id)).where(Appointment.status == "cancelled")
        )).scalar()
        completed = (await db.execute(
            select(func.count(Appointment.id)).where(Appointment.status == "completed")
        )).scalar()

    return {
        "total_users": total_users,
        "total_patients": total_patients,
        "total_doctors": total_doctors,
        "total_appointments": total_appointments,
        "today_appointments": today_appointments,
        "active_sessions": active_sessions,
        "upcoming_sessions": total_sessions,
        "no_shows": no_shows,
        "cancellations": cancellations,
        "completed": completed,
    }


# ─── All Users ─────────────────────────────────────────────────────────────

@router.get("/users")
async def get_all_users(
    role: str = Query("", description="Filter by role"),
    user: dict = Depends(get_current_user)
):
    await _require_staff(user)
    async with async_session() as db:
        stmt = select(User).order_by(User.created_at.desc())
        if role:
            stmt = stmt.where(User.role == role)
        result = await db.execute(stmt)
        users = result.scalars().all()

        # Build response with patient/doctor details
        user_list = []
        for u in users:
            entry = {
                "id": str(u.id), "email": u.email, "full_name": u.full_name,
                "phone": u.phone or "", "role": u.role, "is_active": u.is_active,
                "created_at": str(u.created_at) if u.created_at else "",
                "gender": "", "blood_group": "", "date_of_birth": "",
                "address": "", "emergency_contact_name": "", "emergency_contact_phone": "",
                "specialization": "", "max_patients_per_day": 0,
            }
            # Get patient details
            pat_r = await db.execute(select(Patient).where(Patient.user_id == u.id))
            pat = pat_r.scalars().first()
            if pat:
                entry["gender"] = pat.gender or ""
                entry["blood_group"] = pat.blood_group or ""
                entry["date_of_birth"] = str(pat.date_of_birth) if pat.date_of_birth else ""
                entry["address"] = pat.address or ""
                entry["emergency_contact_name"] = pat.emergency_contact_name or ""
                entry["emergency_contact_phone"] = pat.emergency_contact_phone or ""
            # Get doctor details
            doc_r = await db.execute(select(Doctor).where(Doctor.user_id == u.id))
            doc = doc_r.scalars().first()
            if doc:
                entry["specialization"] = doc.specialization or ""
                entry["max_patients_per_day"] = doc.max_patients_per_day or 0
            user_list.append(entry)

    return {"users": user_list}


# ─── All Doctors with Stats ───────────────────────────────────────────────

@router.get("/doctors")
async def get_all_doctors(user: dict = Depends(get_current_user)):
    await _require_staff(user)
    async with async_session() as db:
        result = await db.execute(
            select(Doctor, User).join(User, Doctor.user_id == User.id)
        )
        rows = result.all()
        doctors = []
        for doctor, doc_user in rows:
            # Count sessions and appointments
            sess_count = (await db.execute(
                select(func.count(Session.id)).where(Session.doctor_id == doctor.id)
            )).scalar()
            appt_count = (await db.execute(
                select(func.count(Appointment.id))
                .join(Session, Appointment.session_id == Session.id)
                .where(Session.doctor_id == doctor.id)
            )).scalar()
            completed_count = (await db.execute(
                select(func.count(Appointment.id))
                .join(Session, Appointment.session_id == Session.id)
                .where(Session.doctor_id == doctor.id, Appointment.status == "completed")
            )).scalar()
            doctors.append({
                "name": doc_user.full_name,
                "email": doc_user.email,
                "specialization": doctor.specialization or "",
                "max_patients_per_day": doctor.max_patients_per_day,
                "total_sessions": sess_count,
                "total_appointments": appt_count,
                "completed_appointments": completed_count,
                "is_active": doc_user.is_active,
            })
    return {"doctors": doctors}


# ─── All Patients with Risk Score ─────────────────────────────────────────

@router.get("/patients")
async def get_all_patients(
    search: str = Query("", description="Search by name or UHID"),
    user: dict = Depends(get_current_user)
):
    await _require_staff(user)
    async with async_session() as db:
        stmt = select(Patient, User).join(User, Patient.user_id == User.id)
        if search:
            stmt = stmt.where(
                (User.full_name.ilike(f"%{search}%")) | (Patient.uhid.ilike(f"%{search}%"))
            )
        stmt = stmt.order_by(Patient.uhid)
        result = await db.execute(stmt)
        rows = result.all()

    return {"patients": [
        {
            "uhid": p.uhid, "name": u.full_name, "email": u.email,
            "phone": u.phone or "", "gender": p.gender or "",
            "blood_group": p.blood_group or "", "risk_score": p.risk_score or 0,
            "is_active": u.is_active,
        }
        for p, u in rows
    ]}


# ─── All Sessions ─────────────────────────────────────────────────────────

@router.get("/sessions")
async def get_all_sessions(
    status: str = Query("", description="Filter by status"),
    doctor_name: str = Query("", description="Filter by doctor"),
    user: dict = Depends(get_current_user)
):
    await _require_staff(user)
    async with async_session() as db:
        stmt = (
            select(Session, Doctor, User)
            .join(Doctor, Session.doctor_id == Doctor.id)
            .join(User, Doctor.user_id == User.id)
            .order_by(Session.session_date.desc(), Session.start_time)
        )
        if status:
            stmt = stmt.where(Session.status == status)
        if doctor_name:
            stmt = stmt.where(User.full_name.ilike(f"%{doctor_name}%"))
        result = await db.execute(stmt)
        rows = result.all()

        sessions = []
        for sess, doctor, doc_user in rows:
            # Count appointments
            appt_count = (await db.execute(
                select(func.count(Appointment.id)).where(Appointment.session_id == sess.id)
            )).scalar()
            sessions.append({
                "id": str(sess.id),
                "doctor": doc_user.full_name,
                "specialization": doctor.specialization or "",
                "date": str(sess.session_date),
                "start_time": str(sess.start_time),
                "end_time": str(sess.end_time),
                "status": sess.status,
                "total_slots": sess.total_slots,
                "booked": appt_count,
                "delay_minutes": sess.delay_minutes,
                "overtime_minutes": sess.overtime_minutes,
            })
    return {"sessions": sessions}


# ─── Admin Session Actions ────────────────────────────────────────────────

@router.post("/sessions/{session_id}/cancel")
async def admin_cancel_session(session_id: str, user: dict = Depends(get_current_user)):
    """Admin cancels any session."""
    await _require_admin(user)
    async with async_session() as db:
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalars().first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        if session.status not in ["scheduled", "active"]:
            raise HTTPException(status_code=400, detail=f"Cannot cancel — session is {session.status}.")

        # Cancel all pending appointments
        appt_r = await db.execute(
            select(Appointment).where(
                Appointment.session_id == session.id,
                Appointment.status.in_(["booked", "checked_in"])
            )
        )
        cancelled = 0
        for appt in appt_r.scalars().all():
            appt.status = "cancelled"
            cancelled += 1

        session.status = "cancelled"
        await db.commit()
    return {"message": f"Session cancelled. {cancelled} appointments cancelled."}


@router.post("/sessions/{session_id}/activate")
async def admin_activate_session(session_id: str, user: dict = Depends(get_current_user)):
    """Admin activates any scheduled session."""
    await _require_admin(user)
    async with async_session() as db:
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalars().first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        if session.status != "scheduled":
            raise HTTPException(status_code=400, detail=f"Cannot activate — session is {session.status}.")
        if session.session_date != date.today():
            raise HTTPException(status_code=400, detail=f"Cannot activate — session is for {session.session_date}, not today.")
        session.status = "active"
        await db.commit()
    return {"message": "Session activated."}


@router.post("/sessions/{session_id}/complete")
async def admin_complete_session(session_id: str, user: dict = Depends(get_current_user)):
    """Admin completes any active session. Marks no-shows and cancellations."""
    await _require_admin(user)
    async with async_session() as db:
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalars().first()
        if not session:
            raise HTTPException(status_code=404, detail="Session not found.")
        if session.status != "active":
            raise HTTPException(status_code=400, detail=f"Cannot complete — session is {session.status}.")

        appt_r = await db.execute(
            select(Appointment, Patient).join(Patient, Appointment.patient_id == Patient.id)
            .where(Appointment.session_id == session.id, Appointment.status.in_(["booked", "checked_in"]))
        )
        no_shows = 0
        cancelled = 0
        for appt, patient in appt_r.all():
            if appt.status == "booked":
                appt.status = "no_show"
                patient.risk_score = (patient.risk_score or 0) + 20
                no_shows += 1
            elif appt.status == "checked_in":
                appt.status = "cancelled"
                cancelled += 1

        session.status = "completed"
        await db.commit()
    return {"message": f"Session completed. No-shows: {no_shows}, Cancelled: {cancelled}."}


# ─── Audit Logs ───────────────────────────────────────────────────────────

@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = Query(50, description="Number of logs to return"),
    action: str = Query("", description="Filter by action type"),
    user: dict = Depends(get_current_user)
):
    await _require_staff(user)
    async with async_session() as db:
        stmt = (
            select(AuditLog, User)
            .join(User, AuditLog.user_id == User.id)
            .order_by(AuditLog.created_at.desc())
        )
        if action:
            stmt = stmt.where(AuditLog.action == action)
        stmt = stmt.limit(limit)
        result = await db.execute(stmt)
        rows = result.all()

        # Resolve UHIDs to patient names
        logs = []
        for log, u in rows:
            details = log.details or {}
            # Look up patient name from UHID
            if details.get("uhid"):
                pat_r = await db.execute(
                    select(Patient, User).join(User, Patient.user_id == User.id)
                    .where(Patient.uhid == details["uhid"])
                )
                pat_row = pat_r.first()
                if pat_row:
                    details["patient_name"] = pat_row[1].full_name
            logs.append({
                "action": log.action,
                "user": u.full_name,
                "target_type": log.target_type or "",
                "details": details,
                "created_at": str(log.created_at) if log.created_at else "",
            })

    return {"logs": logs}


# ─── Toggle User Active Status ───────────────────────────────────────────

@router.post("/toggle-user/{user_id}")
async def toggle_user_status(user_id: str, user: dict = Depends(get_current_user)):
    await _require_admin(user)
    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        target = result.scalars().first()
        if not target:
            raise HTTPException(status_code=404, detail="User not found.")
        target.is_active = not target.is_active
        await db.commit()
    status = "activated" if target.is_active else "deactivated"
    return {"message": f"User {target.full_name} {status}."}


# ─── Edit Any User ────────────────────────────────────────────────────────

from pydantic import BaseModel

class AdminEditUserRequest(BaseModel):
    full_name: str = ""
    phone: str = ""
    email: str = ""
    role: str = ""
    # Patient-specific
    gender: str = ""
    blood_group: str = ""
    date_of_birth: str = ""
    address: str = ""
    emergency_contact_name: str = ""
    emergency_contact_phone: str = ""
    # Doctor-specific
    specialization: str = ""
    max_patients_per_day: int = 0


@router.put("/users/{user_id}")
async def admin_edit_user(user_id: str, req: AdminEditUserRequest, user: dict = Depends(get_current_user)):
    """Admin can edit any user's full details."""
    await _require_admin(user)
    async with async_session() as db:
        result = await db.execute(select(User).where(User.id == user_id))
        target = result.scalars().first()
        if not target:
            raise HTTPException(status_code=404, detail="User not found.")

        # Update user fields
        if req.full_name:
            target.full_name = req.full_name
        if req.phone:
            target.phone = req.phone
        if req.email:
            target.email = req.email
        if req.role:
            target.role = req.role

        # Update patient fields if patient
        pat_r = await db.execute(select(Patient).where(Patient.user_id == target.id))
        patient = pat_r.scalars().first()
        if patient:
            if req.gender:
                patient.gender = req.gender
            if req.blood_group:
                patient.blood_group = req.blood_group
            if req.date_of_birth:
                try:
                    from datetime import datetime as dt
                    patient.date_of_birth = dt.strptime(req.date_of_birth, "%Y-%m-%d").date()
                except ValueError:
                    pass
            if req.address:
                patient.address = req.address
            if req.emergency_contact_name:
                patient.emergency_contact_name = req.emergency_contact_name
            if req.emergency_contact_phone:
                patient.emergency_contact_phone = req.emergency_contact_phone

        # Update doctor fields if doctor
        doc_r = await db.execute(select(Doctor).where(Doctor.user_id == target.id))
        doctor = doc_r.scalars().first()
        if doctor:
            if req.specialization:
                doctor.specialization = req.specialization
            if req.max_patients_per_day > 0:
                doctor.max_patients_per_day = req.max_patients_per_day

        await db.commit()
    return {"message": f"User {target.full_name} updated."}
