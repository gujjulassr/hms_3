"""
Advanced Python — Regex validation for emails, phone numbers, UHIDs, dates, times.
Section 2 requirement: regex validation for email/phone.
"""
import re
from datetime import datetime


# ── Compiled regex patterns ───────────────────────────────────────────────

EMAIL_PATTERN = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
PHONE_PATTERN = re.compile(r'^[\d\s\+\-\(\)]{7,15}$')
UHID_PATTERN = re.compile(r'^HMS-\d{4}-\d{5}$')
TIME_24H_PATTERN = re.compile(r'^([01]\d|2[0-3]):([0-5]\d)$')
DATE_PATTERN = re.compile(r'^\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])$')
NAME_PATTERN = re.compile(r'^[A-Za-z\s\.\-]{2,100}$')
PASSWORD_PATTERN = re.compile(r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,}$')
BLOOD_GROUP_PATTERN = re.compile(r'^(A|B|AB|O)[+-]$')


# ── Validation functions ──────────────────────────────────────────────────

def validate_email(email: str) -> bool:
    """Validate email format using regex."""
    return bool(EMAIL_PATTERN.match(email))


def validate_phone(phone: str) -> bool:
    """Validate phone number format using regex."""
    return bool(PHONE_PATTERN.match(phone))


def validate_uhid(uhid: str) -> bool:
    """Validate HMS UHID format (HMS-YYYY-NNNNN)."""
    return bool(UHID_PATTERN.match(uhid))


def validate_time_24h(time_str: str) -> bool:
    """Validate 24-hour time format (HH:MM)."""
    return bool(TIME_24H_PATTERN.match(time_str))


def validate_date(date_str: str) -> bool:
    """Validate date format (YYYY-MM-DD)."""
    if not DATE_PATTERN.match(date_str):
        return False
    try:
        datetime.strptime(date_str, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def validate_name(name: str) -> bool:
    """Validate person name (letters, spaces, dots, hyphens, 2-100 chars)."""
    return bool(NAME_PATTERN.match(name))


def validate_password(password: str) -> bool:
    """Validate password strength (min 8 chars, 1 upper, 1 lower, 1 digit)."""
    return bool(PASSWORD_PATTERN.match(password))


def validate_blood_group(bg: str) -> bool:
    """Validate blood group format (A+, B-, AB+, O-, etc.)."""
    return bool(BLOOD_GROUP_PATTERN.match(bg))


def validate_rating(rating: int) -> bool:
    """Validate rating is between 1 and 5."""
    return 1 <= rating <= 5


# ── Sanitization using regex ─────────────────────────────────────────────

def sanitize_name(name: str) -> str:
    """Remove non-alpha characters except spaces, dots, hyphens."""
    return re.sub(r'[^A-Za-z\s\.\-]', '', name).strip()


def extract_uhid_from_text(text: str) -> str:
    """Extract UHID from free text using regex."""
    match = re.search(r'HMS-\d{4}-\d{5}', text)
    return match.group(0) if match else ""


def extract_time_from_text(text: str) -> str:
    """Extract 24h time (HH:MM) from free text."""
    match = re.search(r'(\d{1,2}:\d{2})', text)
    return match.group(1) if match else ""
