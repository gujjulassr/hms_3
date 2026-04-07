from langchain_core.tools import tool
from sqlalchemy import select
from models.patient import Patient
from models.user import User
from models.beneficiary import Beneficiary
from config.database import AsyncSessionLocal as async_session
import uuid
from datetime import datetime
from services.audit import log_action


@tool
async def search_patients(query: str) -> str:
    """Search patients by name or UHID."""
    async with async_session() as db:
        stmt = select(Patient, User).join(User, Patient.user_id == User.id).where(
            (User.full_name.ilike(f"%{query}%")) | (Patient.uhid.ilike(f"%{query}%"))
        )
        result = await db.execute(stmt)
        rows = result.all()

    if not rows:
        return "No patients found."

    output = ""
    for patient, user in rows:
        output += f"UHID: {patient.uhid}, Name: {user.full_name}, Blood Group: {patient.blood_group}, Gender: {patient.gender}\n"
    return output


@tool
async def get_patient_details(query: str) -> str:
    """Get full details of a patient by name or UHID."""
    async with async_session() as db:
        stmt = select(Patient, User).join(User, Patient.user_id == User.id).where(
            (User.full_name.ilike(f"%{query}%")) | (Patient.uhid == query)
        )
        result = await db.execute(stmt)
        row = result.first()

    if not row:
        return "Patient not found."

    patient, user = row
    return (
        f"UHID: {patient.uhid}\n"
        f"Name: {user.full_name}\n"
        f"Email: {user.email}\n"
        f"Phone: {user.phone}\n"
        f"Blood Group: {patient.blood_group}\n"
        f"Gender: {patient.gender}\n"
        f"DOB: {patient.date_of_birth}\n"
        f"Address: {patient.address}\n"
        f"Emergency Contact: {patient.emergency_contact_name} ({patient.emergency_contact_phone})\n"
        f"Risk Score: {patient.risk_score}\n"
    )


@tool
async def register_patient(full_name: str, email: str, phone: str, gender: str, blood_group: str,
                           date_of_birth: str = "", address: str = "",
                           emergency_contact_name: str = "", emergency_contact_phone: str = "",
                           password: str = "password123") -> str:
    """Register a new patient in the system. Returns their UHID.
    Required fields: full_name, email, phone, gender, blood_group.
    Optional: date_of_birth (YYYY-MM-DD), address, emergency_contact_name, emergency_contact_phone, password.
    IMPORTANT: Collect ALL required fields before calling this tool. Ask the user for any missing fields."""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    # Validate required fields
    if not full_name or not email or not phone or not gender or not blood_group:
        return "Missing required fields. Please provide: full_name, email, phone, gender, blood_group."

    async with async_session() as db:
        # Check duplicate email
        existing = await db.execute(select(User).where(User.email == email))
        if existing.scalars().first():
            return f"Email '{email}' is already registered."

        # Generate UHID
        result = await db.execute(select(Patient).order_by(Patient.uhid.desc()))
        last_patient = result.scalars().first()
        if last_patient:
            last_number = int(last_patient.uhid.split("-")[-1])
            new_uhid = f"HMS-{datetime.now().year}-{str(last_number + 1).zfill(5)}"
        else:
            new_uhid = f"HMS-{datetime.now().year}-00001"

        # Parse DOB
        dob = None
        if date_of_birth:
            try:
                dob = datetime.strptime(date_of_birth, "%Y-%m-%d").date()
            except ValueError:
                pass

        new_user = User(
            id=uuid.uuid4(),
            email=email, phone=phone,
            password_hash=pwd_context.hash(password),
            full_name=full_name,
            role="patient", is_active=True
        )
        db.add(new_user)
        await db.flush()

        new_patient = Patient(
            id=uuid.uuid4(),
            user_id=new_user.id,
            uhid=new_uhid,
            gender=gender,
            blood_group=blood_group,
            date_of_birth=dob,
            address=address,
            emergency_contact_name=emergency_contact_name,
            emergency_contact_phone=emergency_contact_phone
        )
        db.add(new_patient)
        await log_action(db, new_user.id, "REGISTER", "patient", new_patient.id,
                         {"uhid": new_uhid, "name": full_name, "email": email})
        await db.commit()

    return f"Patient registered! UHID: {new_uhid}, Name: {full_name}, Email: {email}. Default password: {password}"


@tool
async def update_patient(
    uhid: str, full_name: str = "", phone: str = "", email: str = "",
    gender: str = "", blood_group: str = "", address: str = "",
    emergency_contact_name: str = "", emergency_contact_phone: str = ""
) -> str:
    """Update patient details. Only provided fields will be updated."""
    async with async_session() as db:
        stmt = select(Patient, User).join(User, Patient.user_id == User.id).where(Patient.uhid == uhid)
        result = await db.execute(stmt)
        row = result.first()
        if not row:
            return "Patient not found."

        patient, user = row
        if full_name: user.full_name = full_name
        if phone: user.phone = phone
        if email: user.email = email
        if gender: patient.gender = gender
        if blood_group: patient.blood_group = blood_group
        if address: patient.address = address
        if emergency_contact_name: patient.emergency_contact_name = emergency_contact_name
        if emergency_contact_phone: patient.emergency_contact_phone = emergency_contact_phone

        await log_action(db, user.id, "UPDATE", "patient", patient.id, {"uhid": uhid})
        await db.commit()

    return "Patient details updated successfully!"


@tool
async def add_beneficiary(patient_uhid: str, name: str, relationship: str = "", phone: str = "", gender: str = "", blood_group: str = "") -> str:
    """Add a beneficiary (family member) for a patient. Also registers them as a patient in the system."""
    from passlib.context import CryptContext
    pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

    async with async_session() as db:
        pat_r = await db.execute(select(Patient).where(Patient.uhid == patient_uhid))
        patient = pat_r.scalars().first()
        if not patient:
            return f"Patient {patient_uhid} not found."

        # Generate UHID
        last = await db.execute(select(Patient).order_by(Patient.uhid.desc()))
        last_patient = last.scalars().first()
        if last_patient:
            last_num = int(last_patient.uhid.split("-")[-1])
            ben_uhid = f"HMS-{datetime.now().year}-{str(last_num + 1).zfill(5)}"
        else:
            ben_uhid = f"HMS-{datetime.now().year}-00001"

        # Create User
        ben_email = f"ben_{ben_uhid.lower().replace('-', '_')}@hms.local"
        ben_user = User(
            id=uuid.uuid4(),
            email=ben_email,
            password_hash=pwd_context.hash("password123"),
            full_name=name,
            phone=phone,
            role="patient",
            is_active=True
        )
        db.add(ben_user)
        await db.flush()

        # Create Patient
        ben_patient = Patient(
            id=uuid.uuid4(),
            user_id=ben_user.id,
            uhid=ben_uhid,
            gender=gender,
            blood_group=blood_group
        )
        db.add(ben_patient)

        # Create Beneficiary link
        ben = Beneficiary(
            id=uuid.uuid4(),
            patient_id=patient.id,
            name=name,
            relationship=relationship,
            phone=phone,
            gender=gender,
            blood_group=blood_group
        )
        db.add(ben)
        await db.commit()

    return f"Beneficiary '{name}' added for patient {patient_uhid}. Registered as patient with UHID: {ben_uhid}."


@tool
async def get_my_beneficiaries(patient_uhid: str) -> str:
    """Get all beneficiaries for a patient, including their UHID for booking."""
    async with async_session() as db:
        pat_r = await db.execute(select(Patient).where(Patient.uhid == patient_uhid))
        patient = pat_r.scalars().first()
        if not patient:
            return f"Patient {patient_uhid} not found."

        ben_r = await db.execute(select(Beneficiary).where(Beneficiary.patient_id == patient.id))
        bens = ben_r.scalars().all()

    if not bens:
        return "No beneficiaries found."

    output = ""
    async with async_session() as db:
        for b in bens:
            # Find UHID by matching name in patients table
            p_r = await db.execute(
                select(Patient, User).join(User, Patient.user_id == User.id)
                .where(User.full_name.ilike(f"%{b.name}%"))
            )
            p_row = p_r.first()
            uhid = p_row[0].uhid if p_row else "Not registered"
            output += f"Name: {b.name}, UHID: {uhid}, Relationship: {b.relationship or 'N/A'}, Phone: {b.phone or 'N/A'}\n"
    return output
