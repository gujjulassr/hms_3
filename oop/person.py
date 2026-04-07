"""
OOP Class Hierarchy — Person → Patient / Doctor
Demonstrates: inheritance, encapsulation, polymorphism, magic methods, abstract methods.
"""
import re
from abc import ABC, abstractmethod
from datetime import date, datetime


class Person(ABC):
    """
    Abstract base class for all people in the HMS system.
    Demonstrates: encapsulation (private attributes), __init__, __repr__, __str__, __eq__,
    abstract methods, property decorators, regex validation.
    """

    def __init__(self, full_name: str, email: str, phone: str = "", role: str = ""):
        self._full_name = full_name
        self.email = email            # Uses setter with regex validation
        self.phone = phone            # Uses setter with regex validation
        self._role = role
        self._created_at = datetime.utcnow()

    # ── Properties with encapsulation ──────────────────────────────────────

    @property
    def full_name(self) -> str:
        return self._full_name

    @full_name.setter
    def full_name(self, value: str):
        if not value or len(value.strip()) < 2:
            raise ValueError("Full name must be at least 2 characters.")
        self._full_name = value.strip()

    @property
    def email(self) -> str:
        return self._email

    @email.setter
    def email(self, value: str):
        """Regex validation for email format."""
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if value and not re.match(pattern, value):
            raise ValueError(f"Invalid email format: {value}")
        self._email = value

    @property
    def phone(self) -> str:
        return self._phone

    @phone.setter
    def phone(self, value: str):
        """Regex validation for phone — digits, spaces, +, -, (), min 7 chars."""
        pattern = r'^[\d\s\+\-\(\)]{7,15}$'
        if value and not re.match(pattern, value):
            raise ValueError(f"Invalid phone format: {value}")
        self._phone = value

    @property
    def role(self) -> str:
        return self._role

    # ── Magic methods ──────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(name='{self._full_name}', email='{self._email}', role='{self._role}')"

    def __str__(self) -> str:
        return f"{self._full_name} ({self._role})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, Person):
            return NotImplemented
        return self._email == other._email

    def __hash__(self) -> int:
        return hash(self._email)

    def __lt__(self, other) -> bool:
        """Enable sorting by name."""
        if not isinstance(other, Person):
            return NotImplemented
        return self._full_name.lower() < other._full_name.lower()

    # ── Abstract methods (polymorphism) ────────────────────────────────────

    @abstractmethod
    def get_dashboard_info(self) -> str:
        """Return role-specific dashboard summary."""
        pass

    @abstractmethod
    def get_permissions(self) -> list[str]:
        """Return list of allowed actions for this role."""
        pass


class PatientOOP(Person):
    """
    Patient class — inherits from Person.
    Demonstrates: method overriding, additional attributes, list comprehension.
    """

    def __init__(self, full_name: str, email: str, uhid: str, phone: str = "",
                 gender: str = "", blood_group: str = "", risk_score: int = 0):
        super().__init__(full_name, email, phone, role="patient")
        self._uhid = uhid
        self._gender = gender
        self._blood_group = blood_group
        self._risk_score = risk_score
        self._appointments: list[dict] = []

    @property
    def uhid(self) -> str:
        return self._uhid

    @property
    def risk_score(self) -> int:
        return self._risk_score

    @risk_score.setter
    def risk_score(self, value: int):
        self._risk_score = max(0, value)  # Never negative

    def add_appointment(self, appointment: dict):
        self._appointments.append(appointment)

    def get_active_appointments(self) -> list[dict]:
        """List comprehension — filter only active appointments."""
        return [a for a in self._appointments if a.get("status") in ("booked", "checked_in", "in_progress")]

    def get_completed_count(self) -> int:
        """List comprehension — count completed."""
        return len([a for a in self._appointments if a.get("status") == "completed"])

    def get_dashboard_info(self) -> str:
        """Override: patient-specific dashboard info."""
        active = len(self.get_active_appointments())
        completed = self.get_completed_count()
        return (f"Patient: {self.full_name} (UHID: {self._uhid})\n"
                f"Active appointments: {active}, Completed: {completed}\n"
                f"Risk score: {self._risk_score}")

    def get_permissions(self) -> list[str]:
        return ["book_appointment", "cancel_appointment", "view_appointments", "submit_rating", "view_details"]

    def __repr__(self) -> str:
        return f"PatientOOP(uhid='{self._uhid}', name='{self.full_name}', risk={self._risk_score})"


class DoctorOOP(Person):
    """
    Doctor class — inherits from Person.
    Demonstrates: method overriding, generator for queue streaming.
    """

    def __init__(self, full_name: str, email: str, specialization: str = "",
                 phone: str = "", max_patients_per_day: int = 30):
        super().__init__(full_name, email, phone, role="doctor")
        self._specialization = specialization
        self._max_patients_per_day = max_patients_per_day
        self._queue: list[dict] = []

    @property
    def specialization(self) -> str:
        return self._specialization

    @property
    def max_patients_per_day(self) -> int:
        return self._max_patients_per_day

    def add_to_queue(self, patient_info: dict):
        self._queue.append(patient_info)

    def queue_generator(self):
        """Generator — yields patients from queue one by one (for streaming)."""
        for patient in sorted(self._queue, key=lambda p: (0 if p.get("is_emergency") else 1, p.get("slot_number", 999))):
            yield patient

    def get_emergency_patients(self) -> list[dict]:
        """Lambda + filter — get only emergency patients."""
        return list(filter(lambda p: p.get("is_emergency", False), self._queue))

    def get_sorted_queue(self) -> list[dict]:
        """Sorted with lambda key — emergency first, then by slot number."""
        return sorted(self._queue, key=lambda p: (0 if p.get("is_emergency") else 1, p.get("slot_number", 999)))

    def get_dashboard_info(self) -> str:
        """Override: doctor-specific dashboard info."""
        emergency_count = len(self.get_emergency_patients())
        return (f"Doctor: {self.full_name} ({self._specialization})\n"
                f"Queue: {len(self._queue)} patients ({emergency_count} emergency)\n"
                f"Max patients/day: {self._max_patients_per_day}")

    def get_permissions(self) -> list[str]:
        return ["view_queue", "call_patient", "complete_appointment", "manage_session", "extend_session", "view_patients"]

    def __repr__(self) -> str:
        return f"DoctorOOP(name='{self.full_name}', spec='{self._specialization}', queue={len(self._queue)})"
