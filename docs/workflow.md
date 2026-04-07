# HMS 3 — Workflow & Flowcharts

## 1. System Architecture

```
+------------------+     +------------------+     +------------------+
|   Streamlit UI   |     |  Google Forms    |     |  Google OAuth    |
|  (Patient/Doc/   |     |  (Registration)  |     |  (Login)         |
|   Admin Dashboard)|     +--------+---------+     +--------+---------+
+--------+---------+              |                         |
         |                        |                         |
         v                        v                         v
+--------+--------------------------------------------------------+
|                    FastAPI Backend (REST API)                     |
|  /api/auth  /api/appointments  /api/doctor  /api/admin  /api/chat|
+--------+----------+----------+-----------+-----------+-----------+
         |          |          |           |           |
         v          v          v           v           v
+--------+--+  +---+---+  +---+----+  +---+---+  +---+---+
| PostgreSQL |  |MongoDB|  |LangGraph|  | Gmail |  |Google |
| (Users,    |  |(Chat  |  |(AI Chat|  | SMTP  |  |Drive  |
|  Patients, |  | History|  | Agents)|  |(Email)|  |(PDF)  |
|  Sessions, |  +-------+  +--------+  +-------+  +-------+
|  Appts)    |
+------------+
```

## 2. Patient Registration Flow

```
Patient visits website / fills Google Form
         |
         v
  [New or Existing?]
         |
    +----+----+
    |         |
  New      Existing
    |         |
    v         v
Register    Login
(UHID       (JWT Token)
generated)    |
    |         |
    +----+----+
         |
         v
   Patient Dashboard
   (My Details, Appointments, Book, Reports, Chat)
```

## 3. Appointment Booking Flow

```
Patient selects Doctor + Date
         |
         v
  Fetch available slots (GET /api/available-slots)
         |
         v
  [Slot available?]
    |          |
   Yes         No
    |          |
    v          v
  Select    "All slots
  Slot      fully booked"
    |
    v
  Confirm Booking
    |
    v
  POST /api/book-appointment
    |
    v
  [Duplicate check] ──No──> Create Appointment
    |                              |
   Yes                             v
    |                        Audit Log
    v                              |
  "Already                         v
   booked"                   Email + Calendar
                             Invite (.ics)
```

## 4. Doctor Session & Queue Flow

```
Doctor creates session (date, start, end, slot duration)
         |
         v
  Session: SCHEDULED
         |
         v
  Doctor activates session (today only)
         |
         v
  Session: ACTIVE
         |
         v
  Patients arrive → Staff/Doctor checks them in
         |
         v
  Queue Order:
  1. EMERGENCY (Priority: CRITICAL)
  2. CHECKED_IN (by slot number)
  3. BOOKED (not arrived yet)
         |
         v
  Doctor calls patient → IN_PROGRESS
         |
         v
  Doctor completes → COMPLETED
    |           |
    v           v
  Delay      LLM generates
  Updated    consultation report
    |           |
    v           v
  Next       PDF → Drive → Email
  Patient    to patient
         |
         v
  Session Complete
    |
    +----> Booked patients → NO_SHOW (risk +20)
    +----> Checked-in patients → CANCELLED (no penalty)
```

## 5. Appointment Status Lifecycle

```
  BOOKED ──────┬──────────> CANCELLED (risk +10)
    |          |
    v          +──────────> RESCHEDULED (no penalty)
  CHECKED_IN                    |
    |                           v
    v                     New BOOKED
  IN_PROGRESS                 (at new slot)
    |
    v
  COMPLETED
    |
    v
  Report Generated
  + Email sent

  Session ends with BOOKED → NO_SHOW (risk +20)
  Session ends with CHECKED_IN → CANCELLED (no penalty)
```

## 6. Chat Agent Flow (LangGraph)

```
User sends message
         |
         v
  [Identify Role]
    |       |       |
 Patient  Doctor  Staff/Admin
    |       |       |
    v       v       v
  Patient  Doctor  Staff
  Agent    Agent   Agent
    |       |       |
    v       v       v
  [LLM decides which tool to call]
         |
         v
  Tool executes (DB query/action)
         |
         v
  [Tool result → LLM formats response]
         |
         v
  Response to user
  (saved to MongoDB)
```

## 7. Google Form Pipeline

```
Patient fills Google Form
         |
         v
  Google Apps Script triggers
         |
         v
  POST /api/auth/google-form-register
         |
         v
  [Validate] email, phone, date, time
         |
         v
  [Lookup Doctor] → found?
    |          |
   Yes         No → "Doctor not found"
    |
    v
  [Check Slot] → available?
    |          |
   Yes         No → "Slot full. Next: HH:MM"
    |
    v
  [Register Patient] (if new)
         |
         v
  [Create Appointment]
         |
         v
  [Send Email + Calendar Invite]
         |
         v
  Return UHID + appointment details
```

## 8. Emergency Flow

```
Doctor/Staff enters patient UHID
         |
         v
  POST /api/doctor/emergency-book
         |
         v
  [Patient registered?]
    |          |
   Yes         No → "Not found"
    |
    v
  [Active session?]
    |          |
   Yes         No → "No active session"
    |
    v
  Create appointment:
    slot_number = 0
    priority = CRITICAL
    is_emergency = True
    status = checked_in
         |
         v
  Added to Emergency Queue
  (shown above normal queue)
```

## 9. Reschedule Flow

```
Patient requests reschedule
         |
         v
  [Find existing appointment]
         |
         v
  [Requested slot available?]
    |          |
   Yes         No → "Slot full. Next: HH:MM"
    |
    v
  Old appointment → status: RESCHEDULED (no risk penalty)
         |
         v
  New appointment → status: BOOKED
         |
         v
  Audit log: RESCHEDULE (old → new)
         |
         v
  Email notification with new calendar invite
```

## 10. Risk Score System

```
  Action                    Risk Change
  ─────────────────────     ───────────
  Cancel appointment        +10
  No-show (session ends)    +20
  Reschedule                 0 (no penalty)
  Check-in but not seen      0 (hospital's fault)

  Risk Score thresholds:
  0-19:  Normal
  20-39: Warning (orange in admin)
  40+:   High risk (red in admin)
```
