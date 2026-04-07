from langchain_core.tools import tool
from sqlalchemy import select, func
from models.rating import Rating
from models.patient import Patient
from models.doctor import Doctor
from models.user import User
from config.database import AsyncSessionLocal as async_session
import uuid


@tool
async def submit_rating(patient_uhid: str, doctor_name: str, rating: int, feedback: str = "") -> str:
    """Submit a rating (1-5) for a doctor after an appointment."""
    if rating < 1 or rating > 5:
        return "Rating must be between 1 and 5."

    async with async_session() as db:
        pat_r = await db.execute(select(Patient).where(Patient.uhid == patient_uhid))
        patient = pat_r.scalars().first()
        if not patient:
            return f"Patient {patient_uhid} not found."

        doc_r = await db.execute(
            select(Doctor, User).join(User, Doctor.user_id == User.id)
            .where(User.full_name.ilike(f"%{doctor_name}%"))
        )
        doc_row = doc_r.first()
        if not doc_row:
            return f"Doctor {doctor_name} not found."
        doctor, doc_user = doc_row

        new_rating = Rating(
            id=uuid.uuid4(),
            patient_id=patient.id,
            doctor_id=doctor.id,
            rating=rating,
            feedback=feedback
        )
        db.add(new_rating)
        await db.commit()

    # Auto-sync to RAG vector store
    try:
        from services.rag_feedback import add_feedback_to_store
        add_feedback_to_store(
            feedback_id=str(new_rating.id),
            patient_name=patient.uhid,
            doctor_name=doc_user.full_name,
            specialization=doctor.specialization or "",
            rating=rating,
            feedback_text=feedback
        )
    except Exception as e:
        print(f"[RAG] Sync failed: {e}")

    return f"Rating submitted: {rating}/5 for Dr. {doc_user.full_name}. Thank you!"


@tool
async def get_doctor_ratings(doctor_name: str) -> str:
    """Get average rating and recent feedback for a doctor."""
    async with async_session() as db:
        doc_r = await db.execute(
            select(Doctor, User).join(User, Doctor.user_id == User.id)
            .where(User.full_name.ilike(f"%{doctor_name}%"))
        )
        doc_row = doc_r.first()
        if not doc_row:
            return f"Doctor {doctor_name} not found."
        doctor, doc_user = doc_row

        avg_r = await db.execute(
            select(func.avg(Rating.rating), func.count(Rating.id))
            .where(Rating.doctor_id == doctor.id)
        )
        avg_row = avg_r.first()
        avg_rating = round(float(avg_row[0]), 1) if avg_row[0] else 0
        total = avg_row[1] or 0

        recent_r = await db.execute(
            select(Rating, Patient, User)
            .join(Patient, Rating.patient_id == Patient.id)
            .join(User, Patient.user_id == User.id)
            .where(Rating.doctor_id == doctor.id)
            .order_by(Rating.created_at.desc()).limit(5)
        )
        recent = recent_r.all()

    output = f"Dr. {doc_user.full_name} — Average: {avg_rating}/5 ({total} ratings)\n"
    if recent:
        output += "Recent feedback:\n"
        for r, pat, u in recent:
            fb = f' — "{r.feedback}"' if r.feedback else ""
            output += f"  {u.full_name}: {r.rating}/5{fb}\n"
    return output


@tool
async def search_feedback(doctor_name: str = "", keyword: str = "") -> str:
    """Search feedback/ratings. Filter by doctor name and/or keyword in feedback text."""
    async with async_session() as db:
        stmt = (select(Rating, Patient, User, Doctor)
                .join(Patient, Rating.patient_id == Patient.id)
                .join(User, Patient.user_id == User.id)
                .join(Doctor, Rating.doctor_id == Doctor.id))

        if doctor_name:
            doc_user_sub = select(Doctor.id).join(User, Doctor.user_id == User.id).where(
                User.full_name.ilike(f"%{doctor_name}%"))
            stmt = stmt.where(Rating.doctor_id.in_(doc_user_sub))

        if keyword:
            stmt = stmt.where(Rating.feedback.ilike(f"%{keyword}%"))

        stmt = stmt.order_by(Rating.created_at.desc()).limit(10)
        result = await db.execute(stmt)
        rows = result.all()

    if not rows:
        return "No feedback found."

    output = ""
    for r, pat, u, doc in rows:
        doc_u_r = await async_session().begin()
        output += f"{r.rating}/5 by {u.full_name} — {r.feedback or 'No comment'}\n"
    return output
