"""
Unit tests for slot utility functions.
Section 6: Slot validation tests, appointment conflict tests.
"""
import pytest
from datetime import time
from services.slot_utils import generate_slot_times, count_slots, is_lunch_time, slot_time_for_number


class TestGenerateSlotTimes:
    def test_basic_slot_generation(self):
        """Generate slots from 09:00-10:00 with 15-min duration."""
        slots = generate_slot_times(time(9, 0), time(10, 0), 15)
        assert len(slots) == 4
        assert slots[0]["slot_number"] == 1
        assert slots[0]["slot_time"] == time(9, 0)
        assert slots[-1]["slot_time"] == time(9, 45)

    def test_lunch_break_blocking(self):
        """Slots should skip the 13:00-13:30 lunch break."""
        slots = generate_slot_times(time(12, 0), time(14, 0), 15)
        slot_times = [s["slot_time"] for s in slots]
        # No slot should start during 13:00-13:29
        for st in slot_times:
            assert not (time(13, 0) <= st < time(13, 30)), f"Slot at {st} is during lunch!"

    def test_lunch_break_exactly_at_boundary(self):
        """Slot ending exactly at lunch start should be included."""
        slots = generate_slot_times(time(12, 0), time(14, 0), 30)
        slot_times = [s["slot_time"] for s in slots]
        assert time(12, 0) in slot_times
        assert time(12, 30) in slot_times
        # 13:00 slot would end at 13:30 — overlaps lunch, should skip
        assert time(13, 0) not in slot_times
        assert time(13, 30) in slot_times

    def test_overtime_extension(self):
        """Overtime should add extra slots beyond end_time."""
        slots_without = generate_slot_times(time(9, 0), time(10, 0), 15)
        slots_with = generate_slot_times(time(9, 0), time(10, 0), 15, overtime_minutes=30)
        assert len(slots_with) > len(slots_without)
        assert len(slots_with) == len(slots_without) + 2  # 30min / 15min = 2 extra

    def test_no_lunch_session(self):
        """Session entirely before lunch should have no lunch gap."""
        slots = generate_slot_times(time(9, 0), time(12, 0), 15)
        assert len(slots) == 12  # 3 hours * 4 slots/hour

    def test_full_day_session(self):
        """Full day 09:00-17:00 should skip lunch correctly."""
        slots = generate_slot_times(time(9, 0), time(17, 0), 15)
        # 8 hours = 32 slots, minus 2 lunch slots (13:00, 13:15) = 30
        assert len(slots) == 30

    def test_empty_session(self):
        """Session with start == end should produce no slots."""
        slots = generate_slot_times(time(9, 0), time(9, 0), 15)
        assert len(slots) == 0

    def test_slot_numbers_sequential(self):
        """Slot numbers should be sequential starting from 1."""
        slots = generate_slot_times(time(9, 0), time(14, 0), 15)
        for i, slot in enumerate(slots):
            assert slot["slot_number"] == i + 1


class TestCountSlots:
    def test_count_matches_generate(self):
        """count_slots should match len(generate_slot_times)."""
        assert count_slots(time(9, 0), time(17, 0), 15) == len(
            generate_slot_times(time(9, 0), time(17, 0), 15))

    def test_count_with_overtime(self):
        count = count_slots(time(9, 0), time(17, 0), 15, overtime_minutes=30)
        assert count == 32  # 30 + 2


class TestIsLunchTime:
    def test_during_lunch(self):
        assert is_lunch_time(time(13, 0)) is True
        assert is_lunch_time(time(13, 15)) is True
        assert is_lunch_time(time(13, 29)) is True

    def test_not_lunch(self):
        assert is_lunch_time(time(12, 59)) is False
        assert is_lunch_time(time(13, 30)) is False
        assert is_lunch_time(time(9, 0)) is False
        assert is_lunch_time(time(17, 0)) is False


class TestSlotTimeForNumber:
    def test_first_slot(self):
        assert slot_time_for_number(time(9, 0), 1, 15) == time(9, 0)

    def test_fifth_slot(self):
        assert slot_time_for_number(time(9, 0), 5, 15) == time(10, 0)

    def test_slot_after_lunch(self):
        """Slot number that falls after lunch should have post-lunch time."""
        # Slot 17 at 15-min intervals from 09:00 = 09:00 + 16*15min = 13:00
        # But 13:00 is lunch, so slot 17 should be 13:30
        slot_t = slot_time_for_number(time(9, 0), 17, 15)
        assert slot_t == time(13, 30)
