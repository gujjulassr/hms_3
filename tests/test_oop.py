"""
Unit tests for OOP classes (Person, PatientOOP, DoctorOOP, ScheduleManager, QueueManager).
Section 6: Tests for OOP hierarchy, Section 3: OOP demonstrations.
"""
import pytest
from datetime import time, date
from oop.person import Person, PatientOOP, DoctorOOP
from oop.schedule_manager import ScheduleManager
from oop.queue_manager import QueueManager, QueueEntry


class TestPersonHierarchy:
    """Test Person abstract class, PatientOOP, DoctorOOP."""

    def test_cannot_instantiate_person(self):
        """Person is abstract — cannot be directly instantiated."""
        with pytest.raises(TypeError):
            Person("Test", "test@test.com")

    def test_patient_creation(self):
        p = PatientOOP("Arjun Mehta", "arjun@test.com", "HMS-2026-00001",
                       phone="+91-9000000001", gender="Male", blood_group="A+")
        assert p.full_name == "Arjun Mehta"
        assert p.uhid == "HMS-2026-00001"
        assert p.role == "patient"

    def test_doctor_creation(self):
        d = DoctorOOP("Dr. Shah", "shah@hms.com", "Cardiology", phone="+91-9876543210")
        assert d.full_name == "Dr. Shah"
        assert d.specialization == "Cardiology"
        assert d.role == "doctor"

    def test_email_validation(self):
        with pytest.raises(ValueError):
            PatientOOP("Test", "invalid-email", "HMS-2026-00001")

    def test_phone_validation(self):
        with pytest.raises(ValueError):
            PatientOOP("Test", "test@test.com", "HMS-2026-00001", phone="abc")

    def test_name_setter(self):
        p = PatientOOP("Test User", "test@test.com", "HMS-2026-00001")
        p.full_name = "New Name"
        assert p.full_name == "New Name"
        with pytest.raises(ValueError):
            p.full_name = ""

    def test_equality(self):
        """Two persons with same email are equal."""
        p1 = PatientOOP("A", "same@test.com", "HMS-2026-00001")
        p2 = PatientOOP("B", "same@test.com", "HMS-2026-00002")
        assert p1 == p2

    def test_inequality(self):
        p1 = PatientOOP("A", "a@test.com", "HMS-2026-00001")
        p2 = PatientOOP("B", "b@test.com", "HMS-2026-00002")
        assert p1 != p2

    def test_sorting(self):
        """Persons sort by name."""
        p1 = PatientOOP("Zebra", "z@test.com", "HMS-2026-00001")
        p2 = PatientOOP("Alpha", "a@test.com", "HMS-2026-00002")
        assert sorted([p1, p2])[0].full_name == "Alpha"

    def test_repr(self):
        p = PatientOOP("Test", "t@test.com", "HMS-2026-00001", risk_score=10)
        assert "HMS-2026-00001" in repr(p)
        assert "risk=10" in repr(p)

    def test_str(self):
        p = PatientOOP("Test User", "t@test.com", "HMS-2026-00001")
        assert str(p) == "Test User (patient)"

    def test_polymorphism_dashboard(self):
        """Different roles return different dashboard info (polymorphism)."""
        patient = PatientOOP("Patient A", "p@test.com", "HMS-2026-00001")
        doctor = DoctorOOP("Doctor B", "d@test.com", "Cardiology")
        assert "Patient:" in patient.get_dashboard_info()
        assert "Doctor:" in doctor.get_dashboard_info()

    def test_polymorphism_permissions(self):
        patient = PatientOOP("Patient A", "p@test.com", "HMS-2026-00001")
        doctor = DoctorOOP("Doctor B", "d@test.com", "Cardiology")
        assert "book_appointment" in patient.get_permissions()
        assert "call_patient" in doctor.get_permissions()

    def test_risk_score_never_negative(self):
        p = PatientOOP("Test", "t@test.com", "HMS-2026-00001", risk_score=5)
        p.risk_score = -10
        assert p.risk_score == 0

    def test_patient_appointments(self):
        p = PatientOOP("Test", "t@test.com", "HMS-2026-00001")
        p.add_appointment({"status": "booked", "time": "09:00"})
        p.add_appointment({"status": "completed", "time": "10:00"})
        p.add_appointment({"status": "cancelled", "time": "11:00"})
        assert len(p.get_active_appointments()) == 1
        assert p.get_completed_count() == 1


class TestDoctorOOP:
    def test_queue_operations(self):
        d = DoctorOOP("Dr. Shah", "shah@hms.com", "Cardiology")
        d.add_to_queue({"uhid": "001", "name": "A", "slot_number": 2, "is_emergency": False})
        d.add_to_queue({"uhid": "002", "name": "B", "slot_number": 1, "is_emergency": True})

        sorted_q = d.get_sorted_queue()
        assert sorted_q[0]["is_emergency"] is True  # Emergency first

    def test_queue_generator(self):
        d = DoctorOOP("Dr. Shah", "shah@hms.com", "Cardiology")
        d.add_to_queue({"uhid": "001", "name": "A", "slot_number": 1, "is_emergency": False})
        d.add_to_queue({"uhid": "002", "name": "B", "slot_number": 2, "is_emergency": False})
        gen = d.queue_generator()
        first = next(gen)
        assert first["slot_number"] == 1

    def test_emergency_filter(self):
        d = DoctorOOP("Dr. Shah", "shah@hms.com", "Cardiology")
        d.add_to_queue({"uhid": "001", "name": "A", "is_emergency": True, "slot_number": 0})
        d.add_to_queue({"uhid": "002", "name": "B", "is_emergency": False, "slot_number": 1})
        emergencies = d.get_emergency_patients()
        assert len(emergencies) == 1
        assert emergencies[0]["uhid"] == "001"


class TestScheduleManager:
    def test_basic_creation(self):
        sm = ScheduleManager(time(9, 0), time(17, 0), 15)
        assert sm.total_slots == 30  # 8h - 30min lunch = 7.5h = 30 slots
        assert len(sm.available_slots) == 30

    def test_binary_search_exact(self):
        sm = ScheduleManager(time(9, 0), time(17, 0), 15)
        result = sm.binary_search_slot(time(10, 0))
        assert result is not None
        assert result["slot_time"] == time(10, 0)

    def test_binary_search_between_slots(self):
        sm = ScheduleManager(time(9, 0), time(17, 0), 15)
        result = sm.binary_search_slot(time(10, 7))
        assert result is not None
        assert result["slot_time"] == time(10, 15)  # Next slot

    def test_binary_search_available(self):
        sm = ScheduleManager(time(9, 0), time(17, 0), 15, max_per_slot=1)
        # Book first slot
        sm.book_slot(1)
        result = sm.binary_search_available_slot(time(9, 0))
        assert result is not None
        assert result["slot_number"] == 2  # First one is booked

    def test_booking(self):
        sm = ScheduleManager(time(9, 0), time(10, 0), 15, max_per_slot=2)
        assert sm.book_slot(1) is True  # First booking
        assert sm.book_slot(1) is True  # Second (overbooking)
        assert sm.book_slot(1) is False  # Third — full

    def test_release_slot(self):
        sm = ScheduleManager(time(9, 0), time(10, 0), 15, max_per_slot=1)
        sm.book_slot(1)
        assert len(sm.available_slots) == 3
        sm.release_slot(1)
        assert len(sm.available_slots) == 4

    def test_lunch_check(self):
        sm = ScheduleManager(time(9, 0), time(17, 0), 15)
        assert sm.is_lunch_time(time(13, 0)) is True
        assert sm.is_lunch_time(time(12, 59)) is False
        assert sm.is_lunch_time(time(13, 30)) is False

    def test_extend(self):
        sm = ScheduleManager(time(9, 0), time(17, 0), 15)
        original = sm.total_slots
        sm.extend(30)
        assert sm.total_slots == original + 2

    def test_morning_afternoon_split(self):
        sm = ScheduleManager(time(9, 0), time(17, 0), 15)
        morning = sm.get_morning_slots()
        afternoon = sm.get_afternoon_slots()
        assert all(s["slot_time"] < time(13, 0) for s in morning)
        assert all(s["slot_time"] >= time(13, 30) for s in afternoon)

    def test_slot_times_map(self):
        sm = ScheduleManager(time(9, 0), time(10, 0), 15)
        times = sm.get_slot_times()
        assert len(times) == 4
        assert times[0] == time(9, 0)

    def test_contains(self):
        sm = ScheduleManager(time(9, 0), time(10, 0), 15)
        assert 1 in sm
        assert 999 not in sm

    def test_len(self):
        sm = ScheduleManager(time(9, 0), time(10, 0), 15)
        assert len(sm) == 4

    def test_iteration(self):
        sm = ScheduleManager(time(9, 0), time(10, 0), 15)
        slots = list(sm)
        assert len(slots) == 4


class TestQueueManager:
    def test_add_and_sort(self):
        qm = QueueManager()
        qm.add_patient(QueueEntry("001", "Normal", 2, time(9, 30)))
        qm.add_patient(QueueEntry("002", "Emergency", 0, time(9, 0), is_emergency=True, priority="CRITICAL"))
        # Emergency should be first
        patients = list(qm.waiting_generator())
        assert patients[0].uhid == "002"
        assert patients[0].is_emergency is True

    def test_call_next(self):
        qm = QueueManager()
        qm.add_patient(QueueEntry("001", "Patient A", 1, time(9, 0)))
        called = qm.call_next()
        assert called is not None
        assert called.uhid == "001"
        assert called.status == "in_progress"
        assert qm.waiting_count == 0

    def test_call_specific(self):
        qm = QueueManager()
        qm.add_patient(QueueEntry("001", "A", 1, time(9, 0)))
        qm.add_patient(QueueEntry("002", "B", 2, time(9, 15)))
        called = qm.call_specific("002")
        assert called is not None
        assert called.uhid == "002"
        assert qm.waiting_count == 1

    def test_complete_reduces_delay(self):
        """Completing early should reduce delay."""
        qm = QueueManager(delay_minutes=10)
        qm.add_patient(QueueEntry("001", "A", 1, time(9, 0)))
        called = qm.call_next()
        # Simulate fast consultation
        from datetime import datetime, timedelta
        called.started_at = datetime.now() - timedelta(minutes=5)
        result = qm.complete_current("001")
        assert result is not None
        assert qm.delay_minutes < 10

    def test_stats(self):
        qm = QueueManager()
        qm.add_patient(QueueEntry("001", "A", 1, time(9, 0)))
        qm.add_patient(QueueEntry("002", "B", 0, time(9, 0), is_emergency=True))
        stats = qm.get_stats()
        assert stats["waiting"] == 2
        assert stats["emergency"] == 1

    def test_doctor_ranking(self):
        data = [
            {"name": "Dr. A", "available_slots": 5, "delay_minutes": 10},
            {"name": "Dr. B", "available_slots": 10, "delay_minutes": 5},
            {"name": "Dr. C", "available_slots": 10, "delay_minutes": 15},
        ]
        ranked = QueueManager.rank_doctors_by_availability(data)
        assert ranked[0]["name"] == "Dr. B"  # Most slots, least delay
        assert ranked[1]["name"] == "Dr. C"  # Same slots as B, more delay

    def test_high_priority_filter(self):
        qm = QueueManager()
        qm.add_patient(QueueEntry("001", "A", 1, time(9, 0), priority="NORMAL"))
        qm.add_patient(QueueEntry("002", "B", 2, time(9, 15), priority="HIGH"))
        qm.add_patient(QueueEntry("003", "C", 0, time(9, 0), priority="CRITICAL", is_emergency=True))
        high = qm.get_high_priority()
        assert len(high) == 2
        assert all(e.priority in ("HIGH", "CRITICAL") for e in high)

    def test_expected_times(self):
        qm = QueueManager(delay_minutes=15)
        qm.add_patient(QueueEntry("001", "A", 1, time(9, 0)))
        expected = qm.get_expected_times(date.today())
        assert len(expected) == 1
        assert expected[0]["expected"] == time(9, 15)  # 9:00 + 15min delay

    def test_bool(self):
        qm = QueueManager()
        assert not qm
        qm.add_patient(QueueEntry("001", "A", 1, time(9, 0)))
        assert qm

    def test_len(self):
        qm = QueueManager()
        qm.add_patient(QueueEntry("001", "A", 1, time(9, 0)))
        qm.add_patient(QueueEntry("002", "B", 2, time(9, 15)))
        assert len(qm) == 2
