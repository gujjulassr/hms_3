"""
ScheduleManager — OOP class for managing doctor sessions and slots.
Demonstrates: encapsulation, list comprehension, generators, binary search (DSA).
"""
from datetime import time, datetime, timedelta
from typing import Optional
from services.slot_utils import generate_slot_times, is_lunch_time


class ScheduleManager:
    """
    Manages a doctor's daily schedule (one session per day).
    Encapsulates slot generation, availability checking, binary search for slot lookup.
    """

    def __init__(self, start_time: time, end_time: time, slot_duration: int = 15,
                 lunch_start: time = time(13, 0), lunch_end: time = time(13, 30),
                 max_per_slot: int = 2, overtime_minutes: int = 0):
        self._start_time = start_time
        self._end_time = end_time
        self._slot_duration = slot_duration
        self._lunch_start = lunch_start
        self._lunch_end = lunch_end
        self._max_per_slot = max_per_slot
        self._overtime_minutes = overtime_minutes
        self._booked_slots: dict[int, int] = {}  # slot_number → count

        # Generate all slots on init (list comprehension over generator)
        self._slots = generate_slot_times(
            start_time, end_time, slot_duration,
            lunch_start, lunch_end, overtime_minutes
        )

    # ── Properties ────────────────────────────────────────────────────────

    @property
    def total_slots(self) -> int:
        return len(self._slots)

    @property
    def available_slots(self) -> list[dict]:
        """List comprehension — only slots with room for more patients."""
        return [s for s in self._slots if self._booked_slots.get(s["slot_number"], 0) < self._max_per_slot]

    @property
    def fully_booked_slots(self) -> list[dict]:
        """List comprehension — slots at capacity."""
        return [s for s in self._slots if self._booked_slots.get(s["slot_number"], 0) >= self._max_per_slot]

    # ── Generators ────────────────────────────────────────────────────────

    def slot_generator(self):
        """Generator — yields each slot one at a time (memory efficient for large schedules)."""
        for slot in self._slots:
            yield slot

    def available_slot_generator(self):
        """Generator — yields only available slots."""
        for slot in self._slots:
            if self._booked_slots.get(slot["slot_number"], 0) < self._max_per_slot:
                yield slot

    # ── Binary Search (DSA) ───────────────────────────────────────────────

    def binary_search_slot(self, target_time: time) -> Optional[dict]:
        """
        Binary search to find the slot closest to or at target_time.
        Slots are pre-sorted by slot_time.
        Returns the slot dict or None if no suitable slot found.
        """
        slots = self._slots
        if not slots:
            return None

        low, high = 0, len(slots) - 1
        result = None

        while low <= high:
            mid = (low + high) // 2
            mid_time = slots[mid]["slot_time"]

            if mid_time == target_time:
                return slots[mid]
            elif mid_time < target_time:
                result = slots[mid]  # Closest so far
                low = mid + 1
            else:
                high = mid - 1

        # Return the closest slot >= target_time
        if result is None:
            return slots[0] if slots else None

        # Check if next slot after result is closer
        idx = slots.index(result)
        if idx + 1 < len(slots):
            next_slot = slots[idx + 1]
            if next_slot["slot_time"] >= target_time:
                return next_slot
        return result

    def binary_search_available_slot(self, target_time: time) -> Optional[dict]:
        """Binary search for the nearest AVAILABLE slot at or after target_time."""
        slot = self.binary_search_slot(target_time)
        if slot and self._booked_slots.get(slot["slot_number"], 0) < self._max_per_slot:
            return slot

        # Linear scan forward from found position for next available
        found = False
        for s in self._slots:
            if s["slot_time"] >= target_time:
                found = True
            if found and self._booked_slots.get(s["slot_number"], 0) < self._max_per_slot:
                return s
        return None

    # ── Booking ───────────────────────────────────────────────────────────

    def book_slot(self, slot_number: int) -> bool:
        """Book a slot. Returns True if successful, False if full."""
        current = self._booked_slots.get(slot_number, 0)
        if current >= self._max_per_slot:
            return False
        self._booked_slots[slot_number] = current + 1
        return True

    def release_slot(self, slot_number: int):
        """Release a booking from a slot."""
        current = self._booked_slots.get(slot_number, 0)
        if current > 0:
            self._booked_slots[slot_number] = current - 1

    def is_lunch_time(self, check_time: time) -> bool:
        """Check if a time falls within lunch break."""
        return is_lunch_time(check_time, self._lunch_start, self._lunch_end)

    # ── Extend session ────────────────────────────────────────────────────

    def extend(self, new_overtime_minutes: int):
        """Extend the session by updating overtime and regenerating slots."""
        self._overtime_minutes = new_overtime_minutes
        self._slots = generate_slot_times(
            self._start_time, self._end_time, self._slot_duration,
            self._lunch_start, self._lunch_end, self._overtime_minutes
        )

    # ── Map / Filter / Lambda ─────────────────────────────────────────────

    def get_slot_times(self) -> list[time]:
        """Map — extract just the times from all slots."""
        return list(map(lambda s: s["slot_time"], self._slots))

    def get_morning_slots(self) -> list[dict]:
        """Filter + lambda — slots before lunch."""
        return list(filter(lambda s: s["slot_time"] < self._lunch_start, self._slots))

    def get_afternoon_slots(self) -> list[dict]:
        """Filter + lambda — slots after lunch."""
        return list(filter(lambda s: s["slot_time"] >= self._lunch_end, self._slots))

    # ── Magic methods ────────────────────────────────────────────────────

    def __repr__(self) -> str:
        return (f"ScheduleManager(start={self._start_time}, end={self._end_time}, "
                f"slots={self.total_slots}, available={len(self.available_slots)})")

    def __len__(self) -> int:
        return self.total_slots

    def __contains__(self, slot_number: int) -> bool:
        return any(s["slot_number"] == slot_number for s in self._slots)

    def __iter__(self):
        return self.slot_generator()
