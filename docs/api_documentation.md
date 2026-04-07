# HMS 3 — API Documentation

Base URL: `http://localhost:8000`

## Authentication
All protected endpoints require: `Authorization: Bearer <JWT_TOKEN>`

---

## Auth Routes (`/api/auth`)

### POST /api/auth/register
Register a new user.
```json
Request: { "email": "str", "password": "str", "full_name": "str", "phone": "str", "role": "patient|doctor|nurse|staff|admin", "gender": "str", "blood_group": "str", "specialization": "str" }
Response: { "message": "Patient registered. UHID: HMS-2026-00001", "uhid": "str" }
```

### POST /api/auth/login
```json
Request: { "email": "str", "password": "str" }
Response: { "token": "jwt_token", "role": "str", "name": "str" }
```

### POST /api/auth/change-password/{email}
```json
Request: { "current_password": "str", "new_password": "str" }
Response: { "message": "Password changed successfully." }
```

### GET /api/auth/google/login
Returns Google OAuth URL.
```json
Response: { "auth_url": "https://accounts.google.com/..." }
```

### GET /api/auth/google/callback?code=xxx
Handles OAuth callback. Auto-registers new users as patients. Redirects to Streamlit with token.

### POST /api/auth/google-form-register
Public endpoint for Google Form integration. Registers + books appointment.
```json
Request: { "full_name": "str", "email": "str", "phone": "str", "preferred_date": "YYYY-MM-DD", "preferred_time": "HH:MM or HH:MMAM", "reason": "str", "doctor_name": "str", "gender": "str", "blood_group": "str", "api_key": "str" }
Response: { "status": "success", "registered": true, "uhid": "str", "appointment": { "doctor": "str", "date": "str", "time": "str", "slot_number": 1 } }
```

---

## Patient Routes (`/api`)

### GET /api/my-profile
Returns logged-in patient's full profile.
```json
Response: { "uhid": "str", "name": "str", "email": "str", "phone": "str", "gender": "str", "blood_group": "str", "date_of_birth": "str", "address": "str", "emergency_contact_name": "str", "emergency_contact_phone": "str" }
```

### PUT /api/my-profile
Update patient profile.
```json
Request: { "full_name": "str", "phone": "str", "gender": "str", "blood_group": "str", "date_of_birth": "YYYY-MM-DD", "address": "str", "emergency_contact_name": "str", "emergency_contact_phone": "str" }
Response: { "message": "Profile updated." }
```

### GET /api/my-appointments
Returns appointments for patient + their beneficiaries.
```json
Response: { "appointments": [{ "patient_name": "str", "patient_uhid": "str", "is_self": true, "doctor": "str", "specialization": "str", "date": "str", "time": "str", "status": "str", "priority": "str" }] }
```

### GET /api/my-reports
Returns consultation reports for patient.
```json
Response: { "reports": [{ "id": "uuid", "doctor": "str", "specialization": "str", "content": "str", "doctor_notes": "str", "drive_link": "str", "created_at": "str" }] }
```

### GET /api/doctors?specialization=Cardiology
List doctors with optional specialization filter.
```json
Response: { "doctors": [{ "name": "str", "specialization": "str", "max_patients_per_day": 30, "upcoming_sessions": 2 }] }
```

### GET /api/available-slots?doctor_name=Sharma&date=2026-04-08
Get available slots for a doctor on a date.
```json
Response: { "doctor": "str", "date": "str", "delay_minutes": 0, "total_available": 28, "slots": [{ "slot_number": 1, "slot_time": "09:00:00", "available_positions": 2, "max_per_slot": 2 }] }
```

### POST /api/book-appointment
Book an appointment.
```json
Request: { "patient_uhid": "str", "doctor_name": "str", "preferred_time": "HH:MM", "preferred_date": "YYYY-MM-DD", "confirm": true }
Response: { "status": "booked", "appointment": { "id": "uuid", "patient_uhid": "str", "doctor": "str", "date": "str", "time": "str", "slot_number": 1 } }
```

### POST /api/cancel-my-appointment
Cancel patient's own appointment.
```json
Request: { "doctor_name": "str" }
Response: { "message": "Appointment cancelled." }
```

### POST /api/reschedule-appointment
Reschedule appointment (no risk penalty).
```json
Request: { "doctor_name": "str", "new_date": "YYYY-MM-DD", "new_time": "HH:MM" }
Response: { "message": "Rescheduled: old → new", "old": { "date": "str", "time": "str" }, "new": { "date": "str", "time": "str" } }
```

### GET /api/my-beneficiaries
Get patient's beneficiaries.
```json
Response: { "beneficiaries": [{ "id": "uuid", "name": "str", "relationship": "str", "phone": "str", "gender": "str", "blood_group": "str", "date_of_birth": "str" }] }
```

### POST /api/my-beneficiaries
Add beneficiary (also registers as patient).
```json
Request: { "name": "str", "relationship": "str", "phone": "str", "email": "str", "gender": "str", "blood_group": "str", "date_of_birth": "YYYY-MM-DD" }
Response: { "message": "Beneficiary added and registered as patient (UHID: ...)", "uhid": "str" }
```

### PUT /api/my-beneficiaries/{ben_id}
Update beneficiary details.

### DELETE /api/my-beneficiaries/{ben_id}
Delete beneficiary.

### GET /api/appointments?patient_uhid=X&doctor_name=Y&date=Z&status=W
Get appointments with filters.

---

## Doctor Routes (`/api/doctor`)

### GET /api/doctor/my-sessions
Get doctor's upcoming sessions.

### POST /api/doctor/create-session
```json
Request: { "session_date": "YYYY-MM-DD", "start_time": "HH:MM", "end_time": "HH:MM", "slot_duration": 15 }
Response: { "message": "Session created... N slots" }
```

### POST /api/doctor/activate-session
Activate today's scheduled session.

### POST /api/doctor/complete-session
Complete active session. Marks no-shows (+20 risk) and cancels checked-in patients (no penalty). Auto-generates consultation reports.

### POST /api/doctor/extend-session
```json
Request: { "extra_minutes": 30 }
```

### POST /api/doctor/cancel-session
```json
Request: { "session_id": "uuid" }
```

### GET /api/doctor/queue
Get real-time queue for active session.
```json
Response: { "session": {...}, "emergency": [...], "in_progress": [...], "waiting": [...], "booked": [...], "delay_minutes": 5 }
```

### POST /api/doctor/checkin-patient
```json
Request: { "patient_uhid": "str" }
```

### POST /api/doctor/call-patient
```json
Request: { "patient_uhid": "str" }
```

### POST /api/doctor/complete-appointment
```json
Request: { "patient_uhid": "str", "notes": "str" }
Response: { "message": "Appointment completed. Report generated.", "delay_minutes": 5 }
```

### POST /api/doctor/cancel-appointment
```json
Request: { "patient_uhid": "str" }
```

### POST /api/doctor/emergency-book
```json
Request: { "patient_uhid": "str" }
Response: { "message": "Emergency: Name (UHID) added to emergency queue." }
```

---

## Admin Routes (`/api/admin`)
*Requires admin/staff/nurse role. User management requires admin only.*

### GET /api/admin/stats
System overview metrics.
```json
Response: { "total_users": 16, "total_patients": 10, "total_doctors": 3, "total_appointments": 20, "today_appointments": 5, "active_sessions": 1, "upcoming_sessions": 3, "no_shows": 2, "cancellations": 4, "completed": 8 }
```

### GET /api/admin/users?role=doctor
All users with full details (patient/doctor specific fields).

### PUT /api/admin/users/{user_id}
Admin edit any user's details.
```json
Request: { "full_name": "str", "phone": "str", "email": "str", "role": "str", "gender": "str", "blood_group": "str", "specialization": "str", ... }
```

### POST /api/admin/toggle-user/{user_id}
Activate/deactivate user. Admin only.

### GET /api/admin/doctors
All doctors with session/appointment stats.

### GET /api/admin/patients?search=Amit
Search patients by name or UHID.

### GET /api/admin/sessions?status=active&doctor_name=Sharma
All sessions with filters.

### POST /api/admin/sessions/{id}/activate
### POST /api/admin/sessions/{id}/cancel
### POST /api/admin/sessions/{id}/complete
Admin session management.

### GET /api/admin/audit-logs?action=BOOK&limit=50
Audit trail with action filter. Returns actor name and resolved patient names.

---

## Chat Routes (`/api/chat`)

### POST /api/chat/message
Send message to LangGraph AI agent (routed by user role).
```json
Request: { "message": "str" }
Response: { "response": "str" }
```

### GET /api/chat/history
Get chat history from MongoDB.

### DELETE /api/chat/history
Clear chat history.

---

## Analytics Routes (`/api/analytics`)

### GET /api/analytics/report?days=30
### GET /api/analytics/busiest-doctors?days=90
### GET /api/analytics/peak-hours?days=30
