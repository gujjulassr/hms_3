# HMS 3 — Hospital Management System
## Comprehensive Project Report

---

## 1. Project Overview

HMS 3 is a full-stack Hospital Management System featuring:
- **Backend:** FastAPI (async) with PostgreSQL
- **Frontend:** Streamlit with role-based dashboards
- **AI:** LangGraph multi-agent chatbot with GPT-4o-mini
- **Speech:** OpenAI Whisper (ASR) + TTS for voice chat
- **RAG:** ChromaDB + OpenAI embeddings for feedback analysis
- **Storage:** PostgreSQL (data), MongoDB (chat history), ChromaDB (vectors), Google Drive (reports)

---

## 2. Technology Stack & Packages

### Core Framework
| Package | Version | Purpose |
|---------|---------|---------|
| fastapi | 0.115.0 | Async REST API framework |
| uvicorn | 0.30.6 | ASGI server |
| streamlit | 1.39.0 | Web UI framework |

### Database & ORM
| Package | Version | Purpose |
|---------|---------|---------|
| sqlalchemy | 2.0.35 | Async ORM for PostgreSQL |
| asyncpg | 0.29.0 | PostgreSQL async driver (non-blocking DB operations) |
| greenlet | 3.1.0 | Lightweight concurrency for SQLAlchemy async |
| pymongo | - | MongoDB driver for chat history persistence |

### Authentication & Security
| Package | Version | Purpose |
|---------|---------|---------|
| pyjwt | 2.9.0 | JWT token creation/validation for stateless auth |
| passlib[bcrypt] | 1.7.4 | Password hashing with bcrypt algorithm |
| python-dotenv | 1.0.1 | Load environment variables from .env |
| google-auth | - | Google OAuth authentication |
| google-auth-oauthlib | - | OAuth 2.0 flow for Google login |

### AI / LLM / Agents
| Package | Version | Purpose |
|---------|---------|---------|
| langgraph | 0.2.53 | Graph-based multi-agent orchestration (state machines for chat agents) |
| langchain | 0.3.7 | Tool abstraction layer for LLM function calling |
| langchain-openai | 0.2.8 | OpenAI GPT-4o-mini integration for chat agents |
| langchain-core | 0.3.19 | Core abstractions (tools, messages, prompts) |
| openai | - | Direct OpenAI API for Whisper ASR, TTS, embeddings, report generation |
| chromadb | - | Vector database for RAG feedback search (persistent, local) |

### Speech (ASR + TTS)
| Package | Purpose |
|---------|---------|
| openai (Whisper) | Speech-to-text — converts patient voice to text |
| openai (tts-1) | Text-to-speech — reads responses aloud (6 voice options) |
| Web Speech API | Browser-native continuous speech recognition (free, no API cost) |

### Report Generation
| Package | Purpose |
|---------|---------|
| fpdf2 | PDF creation for consultation reports |
| google-api-python-client | Google Drive upload for report sharing |

### Email & Notifications
| Package | Purpose |
|---------|---------|
| smtplib (stdlib) | Gmail SMTP for sending emails |
| email (stdlib) | MIME construction for HTML emails + .ics calendar attachments |

### Data Science & Analytics
| Package | Version | Purpose |
|---------|---------|---------|
| pandas | >=2.0.0 | Data manipulation for appointment analytics |
| numpy | >=1.24.0 | Statistical analysis for peak hour prediction |
| matplotlib | >=3.7.0 | Chart generation (bar, pie, line charts) |

### Testing
| Package | Version | Purpose |
|---------|---------|---------|
| pytest | >=7.4.0 | Unit and integration test runner |
| pytest-asyncio | >=0.21.0 | Async test support for FastAPI endpoints |
| httpx | >=0.24.0 | Async HTTP client for API testing |

### Utilities
| Package | Purpose |
|---------|---------|
| requests | HTTP client for Streamlit → FastAPI communication |
| python-multipart | Form data parsing for file uploads (voice) |
| streamlit-autorefresh | Auto-refresh for doctor queue (10s polling) |

---

## 3. Directory Structure

```
hms_3/
├── main.py                          # FastAPI entry point, CORS, lifespan
├── requirements.txt                 # Python dependencies
├── .env / .env.example              # Environment configuration
├── seed.py / seed_api.sh            # Database seeding scripts
├── test_cases.sh                    # 81 E2E test cases (bash)
├── google_form_script.js            # Google Form → API integration
├── sample_logins.txt                # Sample credentials
│
├── config/                          # Configuration
│   ├── database.py                  # SQLAlchemy async engine + session factory
│   ├── auth.py                      # JWT creation/decoding, HTTPBearer
│   └── settings.py                  # App settings from env
│
├── models/                          # SQLAlchemy ORM (10 tables)
│   ├── base.py                      # DeclarativeBase
│   ├── user.py                      # Users (all roles)
│   ├── patient.py                   # Patient profile + UHID + risk_score
│   ├── doctor.py                    # Doctor specialization + capacity
│   ├── session.py                   # Doctor daily sessions + lunch block
│   ├── appointment.py               # Appointments with status lifecycle
│   ├── beneficiary.py               # Patient family members
│   ├── rating.py                    # Patient feedback (1-5 stars)
│   ├── report.py                    # LLM-generated consultation reports
│   └── audit_log.py                 # Action audit trail
│
├── api/routes/                      # REST API (48 endpoints)
│   ├── auth.py                      # Register, Login, Google OAuth, Form register
│   ├── appointments.py              # Profile, Booking, Slots, Beneficiaries, Reschedule
│   ├── doctor_dashboard.py          # Sessions, Queue, Check-in, Call, Complete, Emergency
│   ├── admin.py                     # Stats, Users, Doctors, Patients, Sessions, Audit
│   ├── chat.py                      # Text chat, Voice chat, TTS, Transcribe
│   └── analytics.py                 # Reports, RAG feedback, Peak hours
│
├── agent/                           # LangGraph Multi-Agent System
│   ├── graph.py                     # Supervisor router (role → agent)
│   ├── patient_agent.py             # Patient chatbot (15 tools)
│   ├── doctor_agent.py              # Doctor chatbot (21 tools)
│   └── staff_agent.py               # Staff/Admin chatbot (35 tools)
│
├── tools/                           # LangChain Tools (40+ tools)
│   ├── appointment_tools.py         # Book, Cancel, Reschedule, Check slots
│   ├── patient_tools.py             # Register, Search, Update, Beneficiaries
│   ├── doctor_tools.py              # Search doctors
│   ├── session_tools.py             # Create, Activate, Complete, Extend, Cancel
│   ├── queue_tools.py               # Check-in, Queue, Call, Complete, Emergency
│   ├── rating_tools.py              # Submit rating, Get ratings, Search feedback
│   ├── report_tools.py              # Generate patient/session reports
│   └── rag_tools.py                 # RAG feedback query, Sync to vector store
│
├── services/                        # Business Logic
│   ├── audit.py                     # Audit logging helper
│   ├── chat_store.py                # MongoDB chat history
│   ├── speech.py                    # Whisper ASR + OpenAI TTS
│   ├── report_generator.py          # LLM report + PDF + Drive upload + Email
│   ├── rag_feedback.py              # ChromaDB RAG system
│   ├── scheduler.py                 # Background auto-complete (120s interval)
│   ├── slot_utils.py                # Slot generation with lunch block
│   └── notifications/service.py     # Email + calendar invites (.ics)
│
├── oop/                             # OOP & DSA Demonstrations
│   ├── person.py                    # Abstract Person → Patient/Doctor hierarchy
│   ├── schedule_manager.py          # Binary search slot management
│   └── queue_manager.py             # Priority queue with sorting
│
├── utils/                           # Advanced Python Utilities
│   ├── validators.py                # Regex validation (email, phone, UHID, etc.)
│   ├── decorators.py                # @log_action, @timer, @require_role, @retry
│   └── threading_utils.py           # Thread-safe booking locks
│
├── analytics/                       # Data Science Module
│   └── reports.py                   # Pandas/NumPy analysis + Matplotlib charts
│
├── streamlit_app/                   # Frontend UI
│   ├── app.py                       # Main app (login, OAuth, routing)
│   ├── views/
│   │   ├── patient_dashboard.py     # Patient UI (6 tabs)
│   │   ├── doctor_dashboard.py      # Doctor UI (4 tabs)
│   │   └── admin_dashboard.py       # Admin/Staff UI (6 tabs)
│   └── components/
│       ├── voice_chat.py            # Voice input component wrapper
│       └── voice_input/index.html   # Web Speech API (continuous ASR)
│
├── tests/                           # Test Suite
│   ├── test_validators.py           # 15 validator tests
│   ├── test_oop.py                  # 39 OOP/DSA tests
│   ├── test_slot_utils.py           # 13 slot generation tests
│   └── test_api.py                  # API integration tests
│
└── docs/                            # Documentation
    ├── PROJECT_REPORT.md            # This file
    ├── workflow.md                  # Flowcharts
    ├── api_documentation.md         # API reference
    ├── test_cases.md                # Test case documentation
    └── sample_dataset.md            # Sample data guide
```

---

## 4. Database Schema (10 Tables)

### users
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| email | String | Unique, indexed |
| password_hash | String | Bcrypt hash |
| full_name | String | Display name |
| phone | String | Contact number |
| role | String | patient/doctor/nurse/staff/admin |
| is_active | Boolean | Account status |
| created_at | DateTime | Registration timestamp |

### patients
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID FK→users | Links to user account |
| uhid | String | Unique Health ID (HMS-YYYY-NNNNN) |
| gender | String | Male/Female/Other |
| blood_group | String | A+/A-/B+/B-/O+/O-/AB+/AB- |
| date_of_birth | Date | DOB |
| address | String | Address |
| emergency_contact_name | String | Emergency contact |
| emergency_contact_phone | String | Emergency phone |
| risk_score | Integer | No-show/cancel penalty (0=good, 40+=high risk) |

### doctors
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID FK→users | Links to user account |
| specialization | String | General Medicine, Cardiology, etc. |
| max_patients_per_day | Integer | Default 30 |

### sessions
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| doctor_id | UUID FK→doctors | Which doctor |
| session_date | Date | One session per doctor per day |
| start_time | Time | e.g. 09:00 |
| end_time | Time | e.g. 17:00 |
| lunch_start | Time | Default 13:00 (auto-blocked) |
| lunch_end | Time | Default 14:00 (auto-blocked) |
| slot_duration_minutes | Integer | Default 15 |
| max_per_slot | Integer | Default 2 (overbooking +1) |
| total_slots | Integer | Auto-calculated excluding lunch |
| status | String | scheduled/active/completed/cancelled |
| delay_minutes | Integer | Dynamic — increases/decreases per consultation |
| overtime_minutes | Integer | Extension beyond end_time |

### appointments
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| session_id | UUID FK→sessions | Which session |
| patient_id | UUID FK→patients | Which patient |
| booked_by | UUID FK→users | Who booked (self or staff) |
| slot_number | Integer | 0=emergency, 1+=normal |
| slot_position | Integer | Position within slot (overbooking) |
| slot_time | Time | Scheduled time |
| status | String | booked/checked_in/in_progress/completed/cancelled/no_show/rescheduled |
| priority | String | NORMAL/HIGH/CRITICAL |
| is_emergency | Boolean | Emergency flag |
| checked_in_at | DateTime | When patient arrived |
| called_at | DateTime | When doctor called |
| started_at | DateTime | Consultation start |
| completed_at | DateTime | Consultation end |
| notes | String | Doctor's notes / visit reason |

### beneficiaries
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| patient_id | UUID FK→patients | Parent patient |
| name | String | Family member name |
| relationship | String | Spouse/Child/Parent/etc. |
| phone | String | Contact |
| gender | String | Gender |
| blood_group | String | Blood group |
| date_of_birth | Date | DOB |

### ratings
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| patient_id | UUID FK→patients | Who rated |
| doctor_id | UUID FK→doctors | Who was rated |
| rating | Integer | 1-5 stars |
| feedback | Text | Free text feedback |
| created_at | DateTime | When submitted |

### consultation_reports
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| appointment_id | UUID FK→appointments | Which appointment |
| doctor_id | UUID FK→doctors | Which doctor |
| patient_id | UUID FK→patients | Which patient |
| content | Text | LLM-generated report |
| doctor_notes | Text | Doctor's input notes |
| drive_link | String | Google Drive shareable URL |
| pdf_path | String | Local PDF file path |
| created_at | DateTime | Generation timestamp |

### audit_logs
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| user_id | UUID FK→users | Who performed the action |
| action | String | BOOK/CANCEL/CHECKIN/CALL/COMPLETE/EMERGENCY/RESCHEDULE/etc. |
| target_type | String | appointment/patient/session/beneficiary |
| target_id | UUID | Target record ID |
| details | JSON | Context (UHID, doctor name, times, etc.) |
| created_at | DateTime | When action occurred |

---

## 5. API Endpoints (48 Total)

### Authentication (6 endpoints)
| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/auth/register | Register patient/doctor/staff |
| POST | /api/auth/login | Email/password login → JWT |
| POST | /api/auth/google-form-register | Google Form → register + book |
| POST | /api/auth/change-password/{email} | Change password |
| GET | /api/auth/google/login | Google OAuth URL |
| GET | /api/auth/google/callback | OAuth callback, auto-register |

### Patient (14 endpoints)
| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/my-profile | Patient profile |
| PUT | /api/my-profile | Update profile |
| GET | /api/my-appointments | Appointments (self + beneficiaries) |
| GET | /api/my-reports | Consultation reports |
| GET | /api/doctors | List/filter doctors |
| GET | /api/available-slots | Available slots for doctor+date |
| POST | /api/book-appointment | Two-step booking |
| POST | /api/cancel-my-appointment | Cancel (risk +10) |
| POST | /api/reschedule-appointment | Reschedule (no penalty) |
| GET | /api/my-beneficiaries | List beneficiaries |
| POST | /api/my-beneficiaries | Add beneficiary (auto-registers) |
| PUT | /api/my-beneficiaries/{id} | Update beneficiary |
| DELETE | /api/my-beneficiaries/{id} | Delete beneficiary |
| GET | /api/appointments | Query with filters |

### Doctor (12 endpoints)
| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/doctor/my-sessions | Upcoming sessions |
| POST | /api/doctor/create-session | Create session |
| POST | /api/doctor/activate-session | Activate (today only) |
| POST | /api/doctor/complete-session | Complete + no-show handling |
| POST | /api/doctor/extend-session | Add overtime |
| POST | /api/doctor/cancel-session | Cancel session |
| GET | /api/doctor/queue | Real-time queue |
| POST | /api/doctor/checkin-patient | Check in patient |
| POST | /api/doctor/call-patient | Call patient |
| POST | /api/doctor/complete-appointment | Complete + report generation |
| POST | /api/doctor/cancel-appointment | Cancel appointment |
| POST | /api/doctor/emergency-book | Emergency booking |

### Chat & Voice (5 endpoints)
| Method | Path | Purpose |
|--------|------|---------|
| POST | /api/chat/message | Text → LangGraph agent → response |
| POST | /api/chat/voice | Audio → Whisper → LLM → TTS → audio |
| POST | /api/chat/speak | Text → TTS audio |
| POST | /api/chat/transcribe | Audio → Whisper → text |
| GET/DELETE | /api/chat/history | Get/clear MongoDB history |

### Admin (11 endpoints)
| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/admin/stats | System overview metrics |
| GET | /api/admin/users | All users + details |
| PUT | /api/admin/users/{id} | Edit any user |
| POST | /api/admin/toggle-user/{id} | Activate/deactivate |
| GET | /api/admin/doctors | Doctors with stats |
| GET | /api/admin/patients | Patients with risk scores |
| GET | /api/admin/sessions | All sessions |
| POST | /api/admin/sessions/{id}/activate | Admin activate |
| POST | /api/admin/sessions/{id}/cancel | Admin cancel |
| POST | /api/admin/sessions/{id}/complete | Admin complete |
| GET | /api/admin/audit-logs | Audit trail |

### Analytics (5 endpoints)
| Method | Path | Purpose |
|--------|------|---------|
| GET | /api/analytics/feedback-rag | RAG feedback search |
| POST | /api/analytics/feedback-sync | Sync to vector store |
| GET | /api/analytics/report | Full analytics |
| GET | /api/analytics/busiest-doctors | Doctor rankings |
| GET | /api/analytics/peak-hours | Peak hour analysis |

---

## 6. LangGraph Agent System

### Architecture
```
User Message → Supervisor Graph → Role Router
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
              Patient Agent   Doctor Agent    Staff Agent
              (15 tools)      (21 tools)     (35 tools)
                    │               │               │
                    ▼               ▼               ▼
              Tool Execution → Database Query → Format Response
                    │
                    ▼
              Save to MongoDB → Return to User
```

### Agent Tools Count
| Agent | Tools | Key Capabilities |
|-------|-------|-----------------|
| Patient | 15 | Book/cancel/reschedule, search doctors, beneficiaries, ratings |
| Doctor | 21 | Queue management, sessions, emergency, search patients, RAG feedback |
| Staff/Admin | 35 | Everything — registration, booking, queue, sessions, analytics, RAG |

### Key Agent Rules
- Always use tools for real-time data (never reuse old context)
- Never auto-select when multiple matches — ask user to pick
- Never execute destructive actions without explicit confirmation
- Today's date injected into system prompt for "today"/"tomorrow" resolution

---

## 7. Advanced Python Concepts

### Object-Oriented Programming (oop/)
- **Abstract Base Classes**: `Person` (ABC) with `@abstractmethod`
- **Inheritance**: `PatientOOP(Person)`, `DoctorOOP(Person)`
- **Encapsulation**: Private attributes with `@property` getters/setters
- **Polymorphism**: `get_dashboard_info()`, `get_permissions()` differ by role
- **Magic Methods**: `__repr__`, `__str__`, `__eq__`, `__hash__`, `__lt__`, `__len__`, `__bool__`, `__contains__`, `__iter__`

### Data Structures & Algorithms (oop/)
- **Binary Search**: `ScheduleManager.binary_search_slot()` — O(log n) slot lookup
- **Priority Queue Sorting**: Emergency → HIGH → NORMAL, then by slot number
- **Timsort**: Python's sorted() with composite lambda keys

### Functional Programming
- **List Comprehensions**: Available slots, active appointments, emergency count
- **Generators**: `slot_generator()`, `waiting_generator()`, `queue_generator()`
- **Lambda**: Sorting keys, filtering, mapping
- **Map/Filter**: `get_slot_times()`, `get_morning_slots()`, `get_emergency_patients()`

### Decorators (utils/decorators.py)
- `@log_action` — Logs function calls (async/sync aware)
- `@timer` — Measures execution time
- `@require_role(*roles)` — Role-based access control
- `@retry(max_attempts, delay)` — Auto-retry with backoff

### Threading (utils/threading_utils.py)
- Per-slot thread locks to prevent double-booking
- `ThreadPoolExecutor` for concurrent booking processing
- `run_async_in_thread()` for bridging async/sync code

### Regex Validation (utils/validators.py)
- Compiled patterns for email, phone, UHID, time, date, name, password, blood group
- Extraction utilities: `extract_uhid_from_text()`, `extract_time_from_text()`

---

## 8. Key Workflows

### Appointment Booking
```
Patient → Select Doctor + Date → View Available Slots → Click Slot →
Confirm → Book (duplicate check) → Email + Calendar Invite → Audit Log
```

### Session Lifecycle
```
Create (scheduled) → Activate (active, today only) → 
Patients: Book → Check-in → Call → Complete (delay updated) →
Session Complete: Booked→no_show(+20), Checked_in→cancelled(0)
```

### Risk Score System
| Action | Risk Change |
|--------|-------------|
| Cancel appointment | +10 |
| No-show (session ends) | +20 |
| Reschedule | 0 (no penalty) |
| Check-in but not seen | 0 (hospital's fault) |

### Google Form Pipeline
```
Patient fills form → Apps Script triggers → POST /api/auth/google-form-register →
Validate (email, phone, time) → Lookup doctor → Check slot → Register (if new) →
Book appointment → Email confirmation + calendar invite
```

### Consultation Report
```
Doctor completes appointment → LLM generates report →
PDF created (fpdf2) → Upload to Google Drive → Email to patient with Drive link
```

### RAG Feedback
```
Patient submits rating → Auto-synced to ChromaDB (embeddings) →
Admin asks "What do patients say about wait times?" →
Semantic search → Retrieve relevant feedback → LLM generates summary
```

---

## 9. Testing Summary

| Category | Tests | Tool |
|----------|-------|------|
| Authentication | 10 | bash (E2E) |
| Patient Profile | 5 | bash (E2E) |
| Doctor Sessions | 7 | bash (E2E) |
| Appointment Booking | 8 | bash (E2E) |
| Queue Flow | 7 | bash (E2E) |
| Cancel | 3 | bash (E2E) |
| Reschedule | 4 | bash (E2E) |
| Emergency | 4 | bash (E2E) |
| Beneficiaries | 5 | bash (E2E) |
| Session Completion | 4 | bash (E2E) |
| Admin | 12 | bash (E2E) |
| Doctors & Slots | 3 | bash (E2E) |
| Chat History | 4 | bash (E2E) |
| Edge Cases | 5 | bash (E2E) |
| OOP Classes | 39 | pytest |
| Validators | 15 | pytest |
| Slot Utils | 13 | pytest |
| **Total** | **148** | |

---

## 10. Configuration (.env)

```env
# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/hms_3

# JWT Auth
JWT_SECRET=hms-chatbot-secret-key-2026
JWT_ALGORITHM=HS256
JWT_EXPIRY_MINUTES=480

# OpenAI (GPT-4o-mini, Whisper, TTS, Embeddings)
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini

# Email (Gmail SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=hms.notify.noreply@gmail.com
SMTP_PASSWORD=app-password

# Google OAuth
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/api/auth/google/callback
GOOGLE_DRIVE_REFRESH_TOKEN=...

# MongoDB (Chat History)
MONGO_URL=mongodb://localhost:27017
MONGO_DB=hms_3

# Google Form
PUBLIC_REGISTER_KEY=hms-register-2026

# App
API_PORT=8000
STREAMLIT_PORT=8501
```

---

## 11. How to Run

```bash
# 1. Clone and setup
git clone https://github.com/gujjulassr/hms_3.git
cd hms_3
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Setup databases
createdb hms_3                    # PostgreSQL
brew services start mongodb-community  # MongoDB

# 3. Configure .env
cp .env.example .env
# Edit .env with your keys

# 4. Start backend
python main.py                    # FastAPI on port 8000

# 5. Seed sample data
bash seed_api.sh

# 6. Start frontend
streamlit run streamlit_app/app.py  # Streamlit on port 8501

# 7. Run tests
bash test_cases.sh                # 81 E2E tests
pytest tests/ -v                  # 67 unit tests
```

---

*Generated for HMS 3 — Hospital Management System*
*GitHub: https://github.com/gujjulassr/hms_3*
