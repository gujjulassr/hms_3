"""
Unit tests for regex validators.
Section 6: Unit tests for validation logic.
"""
import pytest
from utils.validators import (
    validate_email, validate_phone, validate_uhid,
    validate_time_24h, validate_date, validate_name,
    validate_password, validate_blood_group, validate_rating,
    sanitize_name, extract_uhid_from_text, extract_time_from_text
)


class TestEmailValidation:
    def test_valid_emails(self):
        assert validate_email("user@example.com") is True
        assert validate_email("test.name@domain.co.in") is True
        assert validate_email("user+tag@gmail.com") is True
        assert validate_email("admin@hms.com") is True

    def test_invalid_emails(self):
        assert validate_email("") is False
        assert validate_email("invalid") is False
        assert validate_email("@domain.com") is False
        assert validate_email("user@") is False
        assert validate_email("user@.com") is False
        assert validate_email("user@domain") is False


class TestPhoneValidation:
    def test_valid_phones(self):
        assert validate_phone("+91-9876543210") is True
        assert validate_phone("9876543210") is True
        assert validate_phone("+1 555-1234567") is True
        assert validate_phone("1234567") is True

    def test_invalid_phones(self):
        assert validate_phone("") is False
        assert validate_phone("123") is False
        assert validate_phone("abc1234567") is False
        assert validate_phone("12345678901234567") is False


class TestUHIDValidation:
    def test_valid_uhids(self):
        assert validate_uhid("HMS-2026-00001") is True
        assert validate_uhid("HMS-2025-12345") is True
        assert validate_uhid("HMS-2024-99999") is True

    def test_invalid_uhids(self):
        assert validate_uhid("") is False
        assert validate_uhid("HMS-2026-1") is False
        assert validate_uhid("12345") is False
        assert validate_uhid("HMS-26-00001") is False
        assert validate_uhid("hms-2026-00001") is False


class TestTimeValidation:
    def test_valid_times(self):
        assert validate_time_24h("09:00") is True
        assert validate_time_24h("13:30") is True
        assert validate_time_24h("23:59") is True
        assert validate_time_24h("00:00") is True

    def test_invalid_times(self):
        assert validate_time_24h("24:00") is False
        assert validate_time_24h("9:00") is False
        assert validate_time_24h("09:60") is False
        assert validate_time_24h("") is False
        assert validate_time_24h("9 AM") is False


class TestDateValidation:
    def test_valid_dates(self):
        assert validate_date("2026-04-07") is True
        assert validate_date("2025-12-31") is True
        assert validate_date("2026-01-01") is True

    def test_invalid_dates(self):
        assert validate_date("") is False
        assert validate_date("2026-13-01") is False
        assert validate_date("2026-02-30") is False
        assert validate_date("07-04-2026") is False
        assert validate_date("2026/04/07") is False


class TestNameValidation:
    def test_valid_names(self):
        assert validate_name("John Doe") is True
        assert validate_name("Dr. Rajesh Shah") is True
        assert validate_name("Mary-Jane") is True

    def test_invalid_names(self):
        assert validate_name("") is False
        assert validate_name("A") is False
        assert validate_name("123 Fake") is False


class TestPasswordValidation:
    def test_valid_passwords(self):
        assert validate_password("Password1") is True
        assert validate_password("MyStr0ngPass") is True
        assert validate_password("Test1234") is True

    def test_invalid_passwords(self):
        assert validate_password("") is False
        assert validate_password("short1A") is False
        assert validate_password("alllowercase1") is False
        assert validate_password("ALLUPPERCASE1") is False
        assert validate_password("NoDigitsHere") is False


class TestBloodGroupValidation:
    def test_valid_blood_groups(self):
        for bg in ["A+", "A-", "B+", "B-", "O+", "O-", "AB+", "AB-"]:
            assert validate_blood_group(bg) is True

    def test_invalid_blood_groups(self):
        assert validate_blood_group("") is False
        assert validate_blood_group("C+") is False
        assert validate_blood_group("A") is False
        assert validate_blood_group("AB") is False


class TestRatingValidation:
    def test_valid_ratings(self):
        for r in [1, 2, 3, 4, 5]:
            assert validate_rating(r) is True

    def test_invalid_ratings(self):
        assert validate_rating(0) is False
        assert validate_rating(6) is False
        assert validate_rating(-1) is False


class TestSanitization:
    def test_sanitize_name(self):
        assert sanitize_name("Dr. Rajesh Shah") == "Dr. Rajesh Shah"
        assert sanitize_name("User@123") == "User"
        assert sanitize_name("  spaces  ") == "spaces"

    def test_extract_uhid(self):
        assert extract_uhid_from_text("Patient HMS-2026-00001 needs help") == "HMS-2026-00001"
        assert extract_uhid_from_text("no uhid here") == ""
        assert extract_uhid_from_text("Book for HMS-2026-12345 at 10:00") == "HMS-2026-12345"

    def test_extract_time(self):
        assert extract_time_from_text("Book at 10:30 please") == "10:30"
        assert extract_time_from_text("no time here") == ""
        assert extract_time_from_text("Available at 9:00 and 14:00") == "9:00"
