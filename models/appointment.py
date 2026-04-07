import uuid
from sqlalchemy import Column, String, Integer, Boolean, DateTime, Time, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from models.base import Base


class Appointment(Base):
    """
    Each appointment belongs to a session slot.
    slot_time = the original scheduled time.
    expected_time = slot_time + session delay (dynamic, calculated at query time).
    """
    __tablename__ = "appointments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False)
    patient_id = Column(UUID(as_uuid=True), ForeignKey("patients.id"), nullable=False)
    booked_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    slot_number = Column(Integer, nullable=False)       # 0 = emergency, 1+ = normal
    slot_position = Column(Integer, default=1)          # position within slot (for overbooking)
    slot_time = Column(Time, nullable=False)            # original scheduled time
    status = Column(String, default="booked")           # booked, checked_in, in_progress, completed, cancelled, no_show
    priority = Column(String, default="NORMAL")         # NORMAL, HIGH, CRITICAL
    is_emergency = Column(Boolean, default=False)
    checked_in_at = Column(DateTime, nullable=True)
    called_at = Column(DateTime, nullable=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    notes = Column(String, nullable=True)
