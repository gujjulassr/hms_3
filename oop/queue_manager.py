"""
QueueManager — OOP class for managing the patient queue.
Demonstrates: encapsulation, sorting (DSA), generators, priority queue logic.
"""
from datetime import datetime, timedelta, time
from typing import Optional


class QueueEntry:
    """Represents a patient in the queue."""

    def __init__(self, uhid: str, name: str, slot_number: int, slot_time: time,
                 is_emergency: bool = False, priority: str = "NORMAL",
                 checked_in_at: Optional[datetime] = None):
        self.uhid = uhid
        self.name = name
        self.slot_number = slot_number
        self.slot_time = slot_time
        self.is_emergency = is_emergency
        self.priority = priority
        self.status = "checked_in"
        self.checked_in_at = checked_in_at or datetime.now()
        self.called_at: Optional[datetime] = None
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    # ── Priority mapping for sorting ──────────────────────────────────────

    @property
    def priority_value(self) -> int:
        """Map priority to numeric value for sorting (lower = higher priority)."""
        mapping = {"CRITICAL": 0, "HIGH": 1, "NORMAL": 2}
        return mapping.get(self.priority, 2)

    def __repr__(self) -> str:
        tag = " [EMERGENCY]" if self.is_emergency else ""
        return f"QueueEntry(uhid='{self.uhid}', name='{self.name}', slot={self.slot_number}{tag})"

    def __lt__(self, other) -> bool:
        """Sorting: emergency first, then by priority, then by slot number."""
        if self.is_emergency != other.is_emergency:
            return self.is_emergency  # Emergency comes first
        if self.priority_value != other.priority_value:
            return self.priority_value < other.priority_value
        return self.slot_number < other.slot_number


class QueueManager:
    """
    Manages the patient queue for a doctor's session.
    Demonstrates: encapsulation, sorting, generators, list comprehension, lambda/filter.
    """

    def __init__(self, delay_minutes: int = 0):
        self._waiting: list[QueueEntry] = []
        self._in_progress: list[QueueEntry] = []
        self._completed: list[QueueEntry] = []
        self._delay_minutes = delay_minutes
        self._slot_duration = 15

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def delay_minutes(self) -> int:
        return self._delay_minutes

    @delay_minutes.setter
    def delay_minutes(self, value: int):
        self._delay_minutes = max(0, value)

    @property
    def waiting_count(self) -> int:
        return len(self._waiting)

    @property
    def emergency_count(self) -> int:
        """List comprehension — count emergencies in waiting."""
        return len([e for e in self._waiting if e.is_emergency])

    # ── Queue operations ──────────────────────────────────────────────────

    def add_patient(self, entry: QueueEntry):
        """Add patient to waiting queue and re-sort."""
        self._waiting.append(entry)
        self._sort_waiting()

    def _sort_waiting(self):
        """
        Sorting algorithm (DSA) — sorts waiting queue.
        Emergency patients first, then by priority level, then by slot number.
        Uses Python's Timsort via sorted() with custom key.
        """
        self._waiting = sorted(
            self._waiting,
            key=lambda e: (
                0 if e.is_emergency else 1,     # Emergency first
                e.priority_value,                 # Then by priority
                e.slot_number                     # Then by slot order
            )
        )

    def call_next(self) -> Optional[QueueEntry]:
        """Call the next patient from the sorted queue."""
        if not self._waiting:
            return None
        entry = self._waiting.pop(0)
        entry.status = "in_progress"
        entry.called_at = datetime.now()
        entry.started_at = datetime.now()
        self._in_progress.append(entry)
        return entry

    def call_specific(self, uhid: str) -> Optional[QueueEntry]:
        """Call a specific patient by UHID."""
        for i, entry in enumerate(self._waiting):
            if entry.uhid == uhid:
                entry = self._waiting.pop(i)
                entry.status = "in_progress"
                entry.called_at = datetime.now()
                entry.started_at = datetime.now()
                self._in_progress.append(entry)
                return entry
        return None

    def complete_current(self, uhid: str) -> Optional[QueueEntry]:
        """Complete a patient's consultation. Updates delay dynamically."""
        for i, entry in enumerate(self._in_progress):
            if entry.uhid == uhid:
                entry = self._in_progress.pop(i)
                entry.status = "completed"
                entry.completed_at = datetime.now()
                self._completed.append(entry)

                # Dynamic delay update
                if entry.started_at:
                    actual = (entry.completed_at - entry.started_at).total_seconds() / 60
                    if actual > self._slot_duration:
                        self._delay_minutes += int(actual - self._slot_duration)
                    elif actual < self._slot_duration and self._delay_minutes > 0:
                        saved = int(self._slot_duration - actual)
                        self._delay_minutes = max(0, self._delay_minutes - saved)

                return entry
        return None

    # ── Generators ────────────────────────────────────────────────────────

    def waiting_generator(self):
        """Generator — yield waiting patients one at a time."""
        for entry in self._waiting:
            yield entry

    def emergency_generator(self):
        """Generator — yield only emergency patients."""
        for entry in self._waiting:
            if entry.is_emergency:
                yield entry

    # ── Doctor availability ranking (DSA — sorting) ──────────────────────

    @staticmethod
    def rank_doctors_by_availability(doctor_data: list[dict]) -> list[dict]:
        """
        Sort doctors by availability (most available first).
        Uses sorting with composite key: available slots desc, then delay asc.
        """
        return sorted(
            doctor_data,
            key=lambda d: (-d.get("available_slots", 0), d.get("delay_minutes", 0))
        )

    # ── Map / Filter / Lambda ────────────────────────────────────────────

    def get_expected_times(self, base_date) -> list[dict]:
        """Map — calculate expected time for each waiting patient accounting for delay."""
        return list(map(
            lambda e: {
                "uhid": e.uhid,
                "name": e.name,
                "scheduled": e.slot_time,
                "expected": (datetime.combine(base_date, e.slot_time) +
                            timedelta(minutes=self._delay_minutes)).time()
            },
            self._waiting
        ))

    def get_high_priority(self) -> list[QueueEntry]:
        """Filter + lambda — get HIGH and CRITICAL priority patients."""
        return list(filter(lambda e: e.priority in ("HIGH", "CRITICAL"), self._waiting))

    # ── Stats ────────────────────────────────────────────────────────────

    def get_stats(self) -> dict:
        """Summary statistics for the queue."""
        return {
            "waiting": self.waiting_count,
            "in_progress": len(self._in_progress),
            "completed": len(self._completed),
            "emergency": self.emergency_count,
            "delay_minutes": self._delay_minutes,
        }

    # ── Magic methods ────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (f"QueueManager(waiting={self.waiting_count}, "
                f"in_progress={len(self._in_progress)}, "
                f"completed={len(self._completed)}, "
                f"delay={self._delay_minutes}min)")

    def __len__(self) -> int:
        return self.waiting_count + len(self._in_progress)

    def __bool__(self) -> bool:
        return self.waiting_count > 0 or len(self._in_progress) > 0

    def __iter__(self):
        return self.waiting_generator()
