from langchain_core.tools import tool
from sqlalchemy import select
from models.doctor import Doctor
from models.user import User
from config.database import AsyncSessionLocal as async_session


@tool
async def search_doctors(query: str = "") -> str:
    """Search doctors by name or specialization. Pass empty string to list all doctors."""
    async with async_session() as db:
        if query:
            stmt = (select(Doctor, User).join(User, Doctor.user_id == User.id)
                    .where((User.full_name.ilike(f"%{query}%")) | (Doctor.specialization.ilike(f"%{query}%"))))
        else:
            stmt = select(Doctor, User).join(User, Doctor.user_id == User.id)
        result = await db.execute(stmt)
        rows = result.all()

    if not rows:
        return "No doctors found."

    output = ""
    for doctor, user in rows:
        output += f"Doctor: {user.full_name}, Specialization: {doctor.specialization}, Max patients/day: {doctor.max_patients_per_day}\n"
    return output
