"""
Slot generation utility.
Generates slot times for a session, automatically skipping the lunch break.
"""
from datetime import datetime, timedelta, time


def generate_slot_times(start_time: time, end_time: time, slot_duration: int,
                        lunch_start: time = time(13, 0), lunch_end: time = time(13, 30),
                        overtime_minutes: int = 0) -> list[dict]:
    """
    Generate slot times skipping lunch break.
    Returns list of {slot_number, slot_time} dicts.
    """
    base_date = datetime(2000, 1, 1)
    current = datetime.combine(base_date, start_time)
    actual_end = datetime.combine(base_date, end_time) + timedelta(minutes=overtime_minutes)
    lunch_s = datetime.combine(base_date, lunch_start)
    lunch_e = datetime.combine(base_date, lunch_end)

    slots = []
    slot_num = 1

    while current + timedelta(minutes=slot_duration) <= actual_end:
        slot_end = current + timedelta(minutes=slot_duration)

        # Check if this slot overlaps with lunch break
        if current < lunch_e and slot_end > lunch_s:
            # Skip to after lunch
            current = lunch_e
            continue

        slots.append({"slot_number": slot_num, "slot_time": current.time()})
        slot_num += 1
        current = slot_end

    return slots


def count_slots(start_time: time, end_time: time, slot_duration: int,
                lunch_start: time = time(13, 0), lunch_end: time = time(13, 30),
                overtime_minutes: int = 0) -> int:
    """Count total slots excluding lunch break."""
    return len(generate_slot_times(start_time, end_time, slot_duration,
                                   lunch_start, lunch_end, overtime_minutes))


def slot_time_for_number(start_time: time, slot_number: int, slot_duration: int,
                         lunch_start: time = time(13, 0), lunch_end: time = time(13, 30)) -> time:
    """Get the time for a specific slot number (skipping lunch)."""
    slots = generate_slot_times(start_time, time(23, 59), slot_duration,
                                lunch_start, lunch_end, overtime_minutes=0)
    for s in slots:
        if s["slot_number"] == slot_number:
            return s["slot_time"]
    return start_time


def is_lunch_time(check_time: time, lunch_start: time = time(13, 0), lunch_end: time = time(13, 30)) -> bool:
    """Check if a time falls within lunch break."""
    return lunch_start <= check_time < lunch_end
