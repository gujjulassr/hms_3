import uuid
from datetime import time
from sqlalchemy import Column, String, Date, Time, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from models.base import Base


class Session(Base):
    """
    ONE session per doctor per day.
    Lunch break (13:00-14:00) is auto-blocked when generating slots.
    Doctor can extend end_time via overtime_minutes.
    """
    __tablename__ = "sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    doctor_id = Column(UUID(as_uuid=True), ForeignKey("doctors.id"), nullable=False)
    session_date = Column(Date, nullable=False, index=True)
    start_time = Column(Time, nullable=False)        # e.g. 09:00
    end_time = Column(Time, nullable=False)           # e.g. 17:00 (original, before overtime)
    lunch_start = Column(Time, default=time(13, 0))    # auto-blocked
    lunch_end = Column(Time, default=time(14, 0))     # auto-blocked
    slot_duration_minutes = Column(Integer, default=15)
    max_per_slot = Column(Integer, default=2)         # +1 overbooking allowed
    total_slots = Column(Integer, default=0)          # auto-calculated excluding lunch
    status = Column(String, default="scheduled")      # scheduled, active, completed, cancelled
    delay_minutes = Column(Integer, default=0)        # dynamic: goes up/down based on consultations
    overtime_minutes = Column(Integer, default=0)     # extension beyond end_time
