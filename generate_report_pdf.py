"""Generate comprehensive HMS 3 Project Report PDF with schemas, tables, and relations."""
from fpdf import FPDF, XPos, YPos
import os

class ReportPDF(FPDF):
    def header(self):
        if self.page_no() > 1:
            self.set_font("Helvetica", "I", 8)
            self.cell(0, 5, "HMS 3 - Hospital Management System - Project Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
            self.set_draw_color(0, 102, 204)
            self.line(10, self.get_y(), 200, self.get_y())
            self.ln(3)

    def footer(self):
        self.set_y(-15)
        self.set_font("Helvetica", "I", 8)
        self.cell(0, 10, f"Page {self.page_no()}/{{nb}}", align="C")

    def chapter_title(self, title):
        self.set_font("Helvetica", "B", 16)
        self.set_text_color(0, 51, 102)
        self.cell(0, 12, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_draw_color(0, 102, 204)
        self.line(10, self.get_y(), 200, self.get_y())
        self.ln(4)
        self.set_text_color(0, 0, 0)

    def section_title(self, title):
        self.set_font("Helvetica", "B", 13)
        self.set_text_color(0, 70, 140)
        self.cell(0, 10, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.set_text_color(0, 0, 0)
        self.ln(1)

    def sub_title(self, title):
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 8, title, new_x=XPos.LMARGIN, new_y=YPos.NEXT)
        self.ln(1)

    def body_text(self, text):
        self.set_font("Helvetica", "", 10)
        self.multi_cell(190, 5, text)
        self.ln(2)

    def bullet(self, text):
        self.set_font("Helvetica", "", 10)
        self.cell(8)
        self.multi_cell(182, 5, "- " + text)

    def table_header(self, cols, widths):
        self.set_font("Helvetica", "B", 9)
        self.set_fill_color(0, 102, 204)
        self.set_text_color(255, 255, 255)
        for i, col in enumerate(cols):
            self.cell(widths[i], 7, col, border=1, fill=True, align="C")
        self.ln()
        self.set_text_color(0, 0, 0)

    def table_row(self, cols, widths, fill=False):
        self.set_font("Helvetica", "", 8)
        if fill:
            self.set_fill_color(240, 245, 255)
        max_h = 7
        for i, col in enumerate(cols):
            self.cell(widths[i], max_h, str(col)[:40], border=1, fill=fill)
        self.ln()

    def check_page_break(self, h=30):
        if self.get_y() + h > 270:
            self.add_page()


def generate_report():
    pdf = ReportPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=20)

    # ═══════════════════════════════════════════════════════════════
    # COVER PAGE
    # ═══════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.ln(40)
    pdf.set_font("Helvetica", "B", 36)
    pdf.set_text_color(0, 51, 102)
    pdf.cell(0, 20, "HMS 3", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_font("Helvetica", "", 18)
    pdf.set_text_color(80, 80, 80)
    pdf.cell(0, 12, "Hospital Management System", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(5)
    pdf.set_draw_color(0, 102, 204)
    pdf.line(60, pdf.get_y(), 150, pdf.get_y())
    pdf.ln(8)
    pdf.set_font("Helvetica", "B", 14)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(0, 10, "Comprehensive Project Report", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(20)
    pdf.set_font("Helvetica", "", 12)
    pdf.cell(0, 8, "Author: Gujjula Samara Simha Reddy", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.cell(0, 8, "GitHub: github.com/gujjulassr/hms_3", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.cell(0, 8, "Date: April 2026", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.ln(20)
    pdf.set_font("Helvetica", "I", 10)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, "FastAPI + Streamlit + LangGraph + PostgreSQL + MongoDB + ChromaDB", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.cell(0, 6, "OpenAI GPT-4o-mini + Whisper ASR + TTS + RAG", new_x=XPos.LMARGIN, new_y=YPos.NEXT, align="C")
    pdf.set_text_color(0, 0, 0)

    # ═══════════════════════════════════════════════════════════════
    # TABLE OF CONTENTS
    # ═══════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_title("Table of Contents")
    toc = [
        "1. Project Overview",
        "2. System Architecture",
        "3. Technology Stack & Packages",
        "4. Database Schema & Relations",
        "5. API Endpoints (48 endpoints)",
        "6. LangGraph Multi-Agent System",
        "7. Services & Business Logic",
        "8. Frontend Dashboards",
        "9. Advanced Python Concepts",
        "10. Key Workflows & Flowcharts",
        "11. Testing (148 test cases)",
        "12. External Integrations",
        "13. Configuration & Deployment",
    ]
    for item in toc:
        pdf.set_font("Helvetica", "", 12)
        pdf.cell(0, 8, item, new_x=XPos.LMARGIN, new_y=YPos.NEXT)

    # ═══════════════════════════════════════════════════════════════
    # 1. PROJECT OVERVIEW
    # ═══════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_title("1. Project Overview")
    pdf.body_text(
        "HMS 3 is a full-stack Hospital Management System designed to handle the complete lifecycle of "
        "hospital operations including patient registration, appointment booking with slot management, "
        "doctor session management, real-time queue tracking with delay calculations, emergency handling, "
        "beneficiary management, feedback collection with RAG-powered analytics, consultation report "
        "generation, and multi-agent AI chatbot for all user roles.\n\n"
        "The system supports 5 user roles: Patient, Doctor, Nurse, Staff, and Admin. Each role has a "
        "dedicated dashboard with role-specific features and a chat interface powered by LangGraph "
        "multi-agent system using GPT-4o-mini."
    )

    pdf.section_title("Key Features")
    features = [
        "Appointment booking with slot management (overbooking support, lunch block)",
        "Real-time queue with dynamic delay tracking",
        "Emergency appointment handling (bypasses normal slots)",
        "Appointment rescheduling (no risk penalty)",
        "Beneficiary management (auto-registers as patient)",
        "LLM-powered consultation report generation (PDF + Google Drive)",
        "Email notifications with calendar invites (.ics)",
        "RAG feedback analysis using ChromaDB + OpenAI embeddings",
        "Voice chat (Web Speech API + OpenAI Whisper + TTS)",
        "Google OAuth login with auto-registration",
        "Google Form integration for external registration + booking",
        "Role-based multi-agent AI chatbot (LangGraph + GPT-4o-mini)",
        "MongoDB persistent chat history",
        "Background scheduler for auto-completing expired sessions",
        "Full audit trail for all system actions",
        "Risk score system for no-shows and cancellations",
    ]
    for f in features:
        pdf.bullet(f)

    # ═══════════════════════════════════════════════════════════════
    # 2. SYSTEM ARCHITECTURE
    # ═══════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_title("2. System Architecture")
    pdf.body_text(
        "The system follows a clean separation between backend (FastAPI REST API) and frontend "
        "(Streamlit). The backend is fully decoupled and can be consumed by any frontend (React, "
        "mobile app, etc.). All communication happens via REST API calls with JWT authentication."
    )

    pdf.section_title("Architecture Components")
    components = [
        ("Frontend", "Streamlit - Role-based dashboards (Patient, Doctor, Admin)"),
        ("Backend", "FastAPI - Async REST API with 48 endpoints"),
        ("Database", "PostgreSQL (asyncpg) - 10 tables for structured data"),
        ("Chat Store", "MongoDB - Persistent chat history"),
        ("Vector DB", "ChromaDB - RAG feedback embeddings"),
        ("AI/LLM", "LangGraph + GPT-4o-mini - Multi-agent chatbot"),
        ("Speech", "OpenAI Whisper (ASR) + TTS-1 + Web Speech API"),
        ("Email", "Gmail SMTP - Notifications + Calendar invites"),
        ("Storage", "Google Drive - Consultation report PDFs"),
        ("Auth", "JWT + Google OAuth 2.0"),
        ("Scheduler", "Background task - Auto-complete expired sessions (120s)"),
    ]
    w = [35, 155]
    pdf.table_header(["Component", "Technology & Purpose"], w)
    for i, (comp, desc) in enumerate(components):
        pdf.table_row([comp, desc], w, fill=i % 2 == 0)

    # ═══════════════════════════════════════════════════════════════
    # 3. TECHNOLOGY STACK
    # ═══════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_title("3. Technology Stack & Packages")

    categories = [
        ("Core Framework", [
            ("fastapi 0.115.0", "Async web framework for REST API"),
            ("uvicorn 0.30.6", "ASGI server for FastAPI"),
            ("streamlit 1.39.0", "Web UI framework for dashboards"),
        ]),
        ("Database & ORM", [
            ("sqlalchemy 2.0.35", "Async ORM for PostgreSQL"),
            ("asyncpg 0.29.0", "PostgreSQL async driver (non-blocking)"),
            ("pymongo", "MongoDB driver for chat history"),
            ("chromadb", "Vector database for RAG feedback"),
        ]),
        ("Authentication", [
            ("pyjwt 2.9.0", "JWT token creation/validation"),
            ("passlib[bcrypt] 1.7.4", "Password hashing (bcrypt)"),
            ("google-auth-oauthlib", "Google OAuth 2.0 flow"),
        ]),
        ("AI / LLM / Agents", [
            ("langgraph 0.2.53", "Graph-based multi-agent orchestration"),
            ("langchain 0.3.7", "Tool abstraction for LLM function calling"),
            ("langchain-openai 0.2.8", "OpenAI GPT-4o-mini integration"),
            ("openai", "Whisper ASR, TTS, embeddings, report gen"),
        ]),
        ("Reports & Email", [
            ("fpdf2", "PDF generation for consultation reports"),
            ("google-api-python-client", "Google Drive API for report upload"),
            ("smtplib (stdlib)", "Gmail SMTP for email notifications"),
        ]),
        ("Data Science", [
            ("pandas >=2.0.0", "Data manipulation for analytics"),
            ("numpy >=1.24.0", "Statistical analysis"),
            ("matplotlib >=3.7.0", "Chart generation"),
        ]),
        ("Testing", [
            ("pytest >=7.4.0", "Unit and integration test runner"),
            ("pytest-asyncio", "Async test support"),
            ("httpx", "Async HTTP client for API testing"),
        ]),
    ]

    for cat_name, packages in categories:
        pdf.check_page_break(40)
        pdf.section_title(cat_name)
        w = [55, 135]
        pdf.table_header(["Package", "Why It's Needed"], w)
        for i, (pkg, reason) in enumerate(packages):
            pdf.table_row([pkg, reason], w, fill=i % 2 == 0)
        pdf.ln(3)

    # ═══════════════════════════════════════════════════════════════
    # 4. DATABASE SCHEMA
    # ═══════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_title("4. Database Schema & Relations")

    pdf.section_title("Entity Relationship Diagram")
    pdf.body_text(
        "The database consists of 10 tables in PostgreSQL with UUID primary keys. "
        "Key relationships:\n"
        "- users (1) --> (1) patients/doctors (role-based extension)\n"
        "- doctors (1) --> (N) sessions (one per day)\n"
        "- sessions (1) --> (N) appointments\n"
        "- patients (1) --> (N) appointments\n"
        "- patients (1) --> (N) beneficiaries\n"
        "- patients (1) --> (N) ratings\n"
        "- appointments (1) --> (1) consultation_reports\n"
        "- users (1) --> (N) audit_logs"
    )

    # Each table
    tables = [
        ("users", "Central user account for all roles", [
            ("id", "UUID PK", "Primary key"),
            ("email", "String UNIQUE", "Login email, indexed"),
            ("password_hash", "String", "Bcrypt hash"),
            ("full_name", "String", "Display name"),
            ("phone", "String", "Contact number"),
            ("role", "String", "patient/doctor/nurse/staff/admin"),
            ("is_active", "Boolean", "Account active status"),
            ("created_at", "DateTime", "Registration timestamp"),
        ]),
        ("patients", "Patient-specific profile data", [
            ("id", "UUID PK", "Primary key"),
            ("user_id", "UUID FK->users", "Links to user account"),
            ("uhid", "String UNIQUE", "Universal Health ID (HMS-YYYY-NNNNN)"),
            ("gender", "String", "Male/Female/Other"),
            ("blood_group", "String", "A+/A-/B+/B-/O+/O-/AB+/AB-"),
            ("date_of_birth", "Date", "Patient DOB"),
            ("address", "String", "Address"),
            ("emergency_contact_name", "String", "Emergency contact person"),
            ("emergency_contact_phone", "String", "Emergency phone"),
            ("risk_score", "Integer", "0=good, +10 cancel, +20 no-show"),
        ]),
        ("doctors", "Doctor-specific profile", [
            ("id", "UUID PK", "Primary key"),
            ("user_id", "UUID FK->users", "Links to user account"),
            ("specialization", "String", "General Medicine, Cardiology, etc."),
            ("max_patients_per_day", "Integer", "Default 30"),
        ]),
        ("sessions", "Doctor daily sessions (one per day)", [
            ("id", "UUID PK", "Primary key"),
            ("doctor_id", "UUID FK->doctors", "Which doctor"),
            ("session_date", "Date", "Session date (indexed)"),
            ("start_time", "Time", "e.g. 09:00"),
            ("end_time", "Time", "e.g. 17:00"),
            ("lunch_start", "Time", "Default 13:00 (auto-blocked)"),
            ("lunch_end", "Time", "Default 14:00 (1hr lunch)"),
            ("slot_duration_minutes", "Integer", "Default 15"),
            ("max_per_slot", "Integer", "Default 2 (overbooking)"),
            ("total_slots", "Integer", "Auto-calculated excl. lunch"),
            ("status", "String", "scheduled/active/completed/cancelled"),
            ("delay_minutes", "Integer", "Dynamic delay tracking"),
            ("overtime_minutes", "Integer", "Extension beyond end_time"),
        ]),
        ("appointments", "Patient appointments with full lifecycle", [
            ("id", "UUID PK", "Primary key"),
            ("session_id", "UUID FK->sessions", "Which session"),
            ("patient_id", "UUID FK->patients", "Which patient"),
            ("booked_by", "UUID FK->users", "Who booked"),
            ("slot_number", "Integer", "0=emergency, 1+=normal"),
            ("slot_position", "Integer", "Position within slot"),
            ("slot_time", "Time", "Scheduled time"),
            ("status", "String", "booked/checked_in/in_progress/completed/cancelled/no_show/rescheduled"),
            ("priority", "String", "NORMAL/HIGH/CRITICAL"),
            ("is_emergency", "Boolean", "Emergency flag"),
            ("checked_in_at", "DateTime", "Patient arrival time"),
            ("called_at", "DateTime", "Doctor called time"),
            ("started_at", "DateTime", "Consultation start"),
            ("completed_at", "DateTime", "Consultation end"),
            ("notes", "String", "Visit reason / doctor notes"),
        ]),
        ("beneficiaries", "Patient family members", [
            ("id", "UUID PK", "Primary key"),
            ("patient_id", "UUID FK->patients", "Parent patient"),
            ("name", "String", "Family member name"),
            ("relationship", "String", "Spouse/Child/Parent/Sibling"),
            ("phone", "String", "Contact"),
            ("gender", "String", "Gender"),
            ("blood_group", "String", "Blood group"),
            ("date_of_birth", "Date", "DOB"),
        ]),
        ("ratings", "Patient feedback for doctors", [
            ("id", "UUID PK", "Primary key"),
            ("patient_id", "UUID FK->patients", "Who rated"),
            ("doctor_id", "UUID FK->doctors", "Who was rated"),
            ("rating", "Integer", "1-5 stars"),
            ("feedback", "Text", "Free text feedback"),
            ("created_at", "DateTime", "Submission time"),
        ]),
        ("consultation_reports", "LLM-generated reports", [
            ("id", "UUID PK", "Primary key"),
            ("appointment_id", "UUID FK->appointments", "Which appointment"),
            ("doctor_id", "UUID FK->doctors", "Which doctor"),
            ("patient_id", "UUID FK->patients", "Which patient"),
            ("content", "Text", "LLM-generated report content"),
            ("doctor_notes", "Text", "Doctor's input notes"),
            ("drive_link", "String", "Google Drive shareable URL"),
            ("pdf_path", "String", "Local PDF file path"),
            ("created_at", "DateTime", "Generation time"),
        ]),
        ("audit_logs", "Full action audit trail", [
            ("id", "UUID PK", "Primary key"),
            ("user_id", "UUID FK->users", "Who performed action"),
            ("action", "String", "BOOK/CANCEL/CHECKIN/CALL/COMPLETE/EMERGENCY/RESCHEDULE..."),
            ("target_type", "String", "appointment/patient/session/beneficiary"),
            ("target_id", "UUID", "Target record ID"),
            ("details", "JSON", "Context: UHID, doctor, times, etc."),
            ("created_at", "DateTime", "Action timestamp"),
        ]),
    ]

    for table_name, description, columns in tables:
        pdf.check_page_break(50)
        pdf.section_title(f"Table: {table_name}")
        pdf.body_text(description)
        w = [35, 40, 115]
        pdf.table_header(["Column", "Type", "Description"], w)
        for i, (col, typ, desc) in enumerate(columns):
            pdf.table_row([col, typ, desc], w, fill=i % 2 == 0)
        pdf.ln(3)

    # ═══════════════════════════════════════════════════════════════
    # 5. API ENDPOINTS
    # ═══════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_title("5. API Endpoints (48 Total)")

    endpoint_groups = [
        ("Authentication (/api/auth) - 6 endpoints", [
            ("POST", "/register", "Register patient/doctor/staff with UHID"),
            ("POST", "/login", "Email/password login, returns JWT"),
            ("POST", "/google-form-register", "Google Form auto-register + book"),
            ("POST", "/change-password/{email}", "Change password"),
            ("GET", "/google/login", "Google OAuth redirect URL"),
            ("GET", "/google/callback", "OAuth callback, auto-register"),
        ]),
        ("Patient (/api) - 14 endpoints", [
            ("GET", "/my-profile", "Patient full profile"),
            ("PUT", "/my-profile", "Update profile details"),
            ("GET", "/my-appointments", "Appointments (self + beneficiaries)"),
            ("GET", "/my-reports", "Consultation reports with Drive links"),
            ("GET", "/doctors", "List/filter doctors by specialization"),
            ("GET", "/available-slots", "Available slots for doctor+date"),
            ("POST", "/book-appointment", "Two-step booking with confirmation"),
            ("POST", "/cancel-my-appointment", "Cancel (risk +10)"),
            ("POST", "/reschedule-appointment", "Reschedule (no penalty)"),
            ("GET", "/my-beneficiaries", "List beneficiaries"),
            ("POST", "/my-beneficiaries", "Add beneficiary (auto-registers)"),
            ("PUT", "/my-beneficiaries/{id}", "Update beneficiary"),
            ("DELETE", "/my-beneficiaries/{id}", "Delete beneficiary"),
            ("GET", "/appointments", "Query with filters"),
        ]),
        ("Doctor (/api/doctor) - 12 endpoints", [
            ("GET", "/my-sessions", "Upcoming sessions"),
            ("POST", "/create-session", "Create session (1 per day)"),
            ("POST", "/activate-session", "Activate (today only)"),
            ("POST", "/complete-session", "Complete + no-show handling"),
            ("POST", "/extend-session", "Add overtime minutes"),
            ("POST", "/cancel-session", "Cancel session"),
            ("GET", "/queue", "Real-time queue (4 categories)"),
            ("POST", "/checkin-patient", "Check in (booked->checked_in)"),
            ("POST", "/call-patient", "Call (checked_in->in_progress)"),
            ("POST", "/complete-appointment", "Complete + report generation"),
            ("POST", "/cancel-appointment", "Cancel appointment"),
            ("POST", "/emergency-book", "Emergency (bypasses slots)"),
        ]),
        ("Chat & Voice (/api/chat) - 6 endpoints", [
            ("POST", "/message", "Text chat via LangGraph agent"),
            ("POST", "/voice", "Audio->Whisper->LLM->TTS->Audio"),
            ("POST", "/speak", "Text to speech (OpenAI TTS)"),
            ("POST", "/transcribe", "Audio to text (Whisper)"),
            ("GET", "/history", "Chat history from MongoDB"),
            ("DELETE", "/history", "Clear chat history"),
        ]),
        ("Admin (/api/admin) - 11 endpoints", [
            ("GET", "/stats", "System overview metrics"),
            ("GET", "/users", "All users with full details"),
            ("PUT", "/users/{id}", "Edit any user (admin only)"),
            ("POST", "/toggle-user/{id}", "Activate/deactivate (admin)"),
            ("GET", "/doctors", "Doctors with session/appt stats"),
            ("GET", "/patients", "Patients with risk scores"),
            ("GET", "/sessions", "All sessions with filters"),
            ("POST", "/sessions/{id}/activate", "Admin activate session"),
            ("POST", "/sessions/{id}/cancel", "Admin cancel session"),
            ("POST", "/sessions/{id}/complete", "Admin complete session"),
            ("GET", "/audit-logs", "Full audit trail"),
        ]),
        ("Analytics (/api/analytics) - 5 endpoints", [
            ("GET", "/feedback-rag", "RAG semantic feedback search"),
            ("POST", "/feedback-sync", "Sync ratings to ChromaDB"),
            ("GET", "/report", "Full analytics dashboard"),
            ("GET", "/busiest-doctors", "Doctor rankings"),
            ("GET", "/peak-hours", "Peak hour analysis"),
        ]),
    ]

    for group_name, endpoints in endpoint_groups:
        pdf.check_page_break(40)
        pdf.section_title(group_name)
        w = [18, 60, 112]
        pdf.table_header(["Method", "Path", "Description"], w)
        for i, (method, path, desc) in enumerate(endpoints):
            pdf.table_row([method, path, desc], w, fill=i % 2 == 0)
        pdf.ln(3)

    # ═══════════════════════════════════════════════════════════════
    # 6. LANGGRAPH AGENTS
    # ═══════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_title("6. LangGraph Multi-Agent System")
    pdf.body_text(
        "The chat system uses LangGraph to create role-specific AI agents. Each agent has access to "
        "different tools based on the user's role. The supervisor graph routes messages to the correct "
        "agent based on the JWT token's role claim. All agents use GPT-4o-mini with function calling."
    )

    pdf.section_title("Agent Architecture")
    pdf.body_text(
        "User Message -> Supervisor Graph -> Role Router\n"
        "  Patient -> Patient Agent (15 tools)\n"
        "  Doctor -> Doctor Agent (21 tools)\n"
        "  Staff/Admin -> Staff Agent (35 tools)\n\n"
        "Each agent: LLM decides tool -> Tool executes (DB query) -> LLM formats response -> "
        "Save to MongoDB -> Return to user"
    )

    agents = [
        ("Patient Agent", "15", "Book/cancel/reschedule appointments, search doctors, manage beneficiaries, submit ratings, view reports"),
        ("Doctor Agent", "21", "Queue management, sessions, emergency booking, search patients, RAG feedback, report generation"),
        ("Staff/Admin Agent", "35", "Everything: registration, booking, queue, sessions, analytics, RAG, audit logs"),
    ]
    w = [35, 15, 140]
    pdf.table_header(["Agent", "Tools", "Capabilities"], w)
    for i, (agent, tools, caps) in enumerate(agents):
        pdf.table_row([agent, tools, caps], w, fill=i % 2 == 0)

    pdf.ln(5)
    pdf.section_title("Key Agent Rules")
    rules = [
        "Always use tools for real-time data (never reuse old chat context)",
        "Never auto-select when multiple matches - ask user to pick",
        "Never execute destructive actions without explicit confirmation",
        "Today's date injected into system prompt for 'today'/'tomorrow' resolution",
        "If search returns multiple results, list all and ask user to choose",
    ]
    for r in rules:
        pdf.bullet(r)

    # ═══════════════════════════════════════════════════════════════
    # 7. SERVICES
    # ═══════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_title("7. Services & Business Logic")

    services = [
        ("Notification Service", "Gmail SMTP emails with calendar invites (.ics) for booking, cancellation, reschedule, check-in, no-show, feedback request, session cancelled"),
        ("Report Generator", "LLM generates consultation report -> FPDF creates PDF -> Google Drive upload -> Email with PDF attachment + Drive link"),
        ("RAG Feedback", "ChromaDB vector store + OpenAI text-embedding-3-small. Semantic search on patient feedback. Generates insightful summaries with themes and patterns"),
        ("Speech Service", "OpenAI Whisper for ASR (speech-to-text), TTS-1 for text-to-speech (6 voice options: alloy, echo, fable, onyx, nova, shimmer)"),
        ("Chat Store", "MongoDB persistence for chat history. Save/retrieve/clear per user email"),
        ("Scheduler", "Background async task (120s interval). Auto-completes expired sessions: booked->no_show (+20 risk), checked_in->cancelled (no penalty)"),
        ("Slot Utils", "Generates time slots from start to end, skipping lunch break (13:00-14:00). Counts slots, checks lunch time"),
        ("Audit Logger", "Structured audit trail with actor, action, target, details JSON. Used across all endpoints"),
    ]

    for name, desc in services:
        pdf.check_page_break(20)
        pdf.sub_title(name)
        pdf.body_text(desc)

    # ═══════════════════════════════════════════════════════════════
    # 8. FRONTEND DASHBOARDS
    # ═══════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_title("8. Frontend Dashboards (Streamlit)")

    dashboards = [
        ("Patient Dashboard (6 tabs)", [
            "My Details - View/edit profile, emergency contact, beneficiaries",
            "My Appointments - Active + past appointments, cancel/reschedule buttons",
            "Book Appointment - Filter by department, select doctor, pick slot, confirm",
            "Reports - View consultation reports with Google Drive links",
            "Beneficiaries - Add/edit/remove family members",
            "Chat - Text + voice chat with AI assistant",
        ]),
        ("Doctor Dashboard (4 tabs)", [
            "Queue - Real-time queue (emergency/in-progress/waiting/booked), check-in/call/complete, emergency booking",
            "Session - Create/activate/extend/cancel sessions, view session list",
            "Patients - Today's patient list with status",
            "Chat - Text + voice chat with AI assistant",
        ]),
        ("Admin Dashboard (6 tabs)", [
            "Overview - System stats (users, patients, doctors, appointments, no-shows)",
            "Doctors - All doctors with stats, filter by department",
            "Sessions - All sessions, filter by date/status/department/doctor, activate/cancel/complete",
            "Users - All users, filter by role, edit all details, activate/deactivate, register new users",
            "Audit Logs - Full audit trail, filter by action type, human-readable format",
            "Chat - Text + voice chat with AI assistant",
        ]),
    ]

    for dash_name, tabs in dashboards:
        pdf.check_page_break(40)
        pdf.section_title(dash_name)
        for tab in tabs:
            pdf.bullet(tab)
        pdf.ln(3)

    # ═══════════════════════════════════════════════════════════════
    # 9. ADVANCED PYTHON
    # ═══════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_title("9. Advanced Python Concepts")

    concepts = [
        ("Object-Oriented Programming", "Abstract Base Classes (ABC), inheritance (Person->Patient/Doctor), encapsulation (private attrs + @property), polymorphism (overridden methods), magic methods (__repr__, __eq__, __hash__, __lt__, __len__, __iter__)"),
        ("Data Structures & Algorithms", "Binary search for O(log n) slot lookup (ScheduleManager), priority queue sorting (emergency first), Timsort with composite lambda keys, thread-safe per-slot locking"),
        ("Functional Programming", "List comprehensions (available_slots, active_appointments), generators (slot_generator, waiting_generator), lambda functions (sorting keys), map/filter (get_slot_times, get_emergency_patients)"),
        ("Decorators", "@log_action (logs function calls), @timer (execution time), @require_role (access control), @retry (auto-retry with backoff). All support async/sync"),
        ("Threading & Concurrency", "Per-slot thread locks (prevent double-booking), ThreadPoolExecutor (concurrent booking), run_async_in_thread bridge. Production uses async/await (asyncpg)"),
        ("Regex Validation", "Compiled patterns for email, phone, UHID (HMS-YYYY-NNNNN), 24h time, date (YYYY-MM-DD), name, password strength, blood group. Text extraction utilities"),
        ("Async/Await", "Full async stack: asyncpg (DB), FastAPI (endpoints), LangGraph (agents), background scheduler (asyncio.sleep loop)"),
    ]

    for name, desc in concepts:
        pdf.check_page_break(25)
        pdf.sub_title(name)
        pdf.body_text(desc)

    # ═══════════════════════════════════════════════════════════════
    # 10. WORKFLOWS
    # ═══════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_title("10. Key Workflows")

    workflows = [
        ("Appointment Booking", "Patient selects doctor+date -> View available slots -> Click slot -> Confirm -> Book (duplicate check) -> Email + calendar invite -> Audit log"),
        ("Session Lifecycle", "Create (scheduled) -> Activate (today only) -> Patients: Book->Check-in->Call->Complete (delay updated) -> Session Complete: booked->no_show(+20), checked_in->cancelled(0)"),
        ("Rescheduling", "Patient requests reschedule -> Check new slot availability -> If full: suggest next available -> Old appointment: status=rescheduled (no risk penalty) -> New appointment: status=booked -> Email notification"),
        ("Emergency", "Doctor/Staff enters UHID -> Create emergency appointment (slot=0, priority=CRITICAL) -> Auto checked-in -> Shows above normal queue -> Doctor calls -> Complete"),
        ("Consultation Report", "Doctor completes appointment -> LLM generates report (diagnosis, prescription, follow-up) -> PDF created -> Google Drive upload -> Email to patient with Drive link + PDF"),
        ("Google Form Pipeline", "Patient fills Google Form -> Apps Script triggers -> POST /api/auth/google-form-register -> Validate -> Register (if new) -> Book appointment -> Email confirmation"),
        ("RAG Feedback", "Patient submits rating -> Auto-synced to ChromaDB -> Admin asks question -> Semantic search -> Retrieve relevant feedback -> LLM generates summary with themes and patterns"),
        ("Risk Score", "Cancel: +10, No-show: +20, Reschedule: 0, Check-in not seen: 0 (hospital fault). Displayed in admin dashboard (color-coded: green/orange/red)"),
    ]

    for name, desc in workflows:
        pdf.check_page_break(20)
        pdf.sub_title(name)
        pdf.body_text(desc)

    # ═══════════════════════════════════════════════════════════════
    # 11. TESTING
    # ═══════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_title("11. Testing (148 Test Cases)")

    pdf.section_title("End-to-End Tests (81 - bash)")
    e2e = [
        ("Authentication", "10", "Login, register, duplicate, wrong password, change password, OAuth"),
        ("Patient Profile", "5", "Get/update profile, verify changes"),
        ("Doctor Sessions", "7", "Create, duplicate, past date, activate, double activate"),
        ("Appointment Booking", "8", "Book, duplicate, overbooking, full slot, non-existent"),
        ("Queue Flow", "7", "Check-in, call, complete, double check-in/complete"),
        ("Cancel", "3", "Cancel booked, already cancelled, patient self-cancel"),
        ("Reschedule", "4", "Free slot, full slot block, no risk penalty"),
        ("Emergency", "4", "Book, queue, duplicate, non-existent"),
        ("Beneficiaries", "5", "Add, get, auto-register, update, delete"),
        ("Session Completion", "4", "Complete, no-show, risk score, cancelled"),
        ("Admin", "12", "Stats, users, filter, doctors, patients, audit, toggle, edit"),
        ("Doctors & Slots", "3", "List, filter, slots"),
        ("Chat History", "4", "Send, history, clear, empty"),
        ("Edge Cases", "5", "Health, root, unauthorized, invalid token, lunch block"),
    ]
    w = [40, 15, 135]
    pdf.table_header(["Category", "Tests", "Coverage"], w)
    for i, (cat, count, coverage) in enumerate(e2e):
        pdf.table_row([cat, count, coverage], w, fill=i % 2 == 0)

    pdf.ln(5)
    pdf.section_title("Unit Tests (67 - pytest)")
    unit = [
        ("OOP Classes", "39", "Person hierarchy, magic methods, polymorphism, list comprehension"),
        ("Validators", "15", "Email, phone, UHID, time, date, name, password, blood group"),
        ("Slot Utils", "13", "Slot generation, lunch block, overtime calculation"),
    ]
    w = [40, 15, 135]
    pdf.table_header(["Module", "Tests", "Coverage"], w)
    for i, (mod, count, coverage) in enumerate(unit):
        pdf.table_row([mod, count, coverage], w, fill=i % 2 == 0)

    # ═══════════════════════════════════════════════════════════════
    # 12. INTEGRATIONS
    # ═══════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_title("12. External Integrations")

    integrations = [
        ("OpenAI GPT-4o-mini", "LLM for chat agents and report generation"),
        ("OpenAI Whisper", "Speech-to-text (ASR) for voice chat"),
        ("OpenAI TTS-1", "Text-to-speech with 6 voice options"),
        ("OpenAI Embeddings", "text-embedding-3-small for RAG vectors"),
        ("Google OAuth 2.0", "Patient auto-registration via Google login"),
        ("Google Drive API", "Upload consultation report PDFs, shareable links"),
        ("Google Forms", "External registration + auto-booking pipeline"),
        ("Gmail SMTP", "Email notifications with calendar invites (.ics)"),
        ("ChromaDB", "Persistent vector database for RAG feedback search"),
        ("MongoDB", "Chat history persistence across sessions"),
        ("Web Speech API", "Browser-native continuous speech recognition (free)"),
    ]
    w = [50, 140]
    pdf.table_header(["Integration", "Purpose"], w)
    for i, (name, purpose) in enumerate(integrations):
        pdf.table_row([name, purpose], w, fill=i % 2 == 0)

    # ═══════════════════════════════════════════════════════════════
    # 13. CONFIGURATION
    # ═══════════════════════════════════════════════════════════════
    pdf.add_page()
    pdf.chapter_title("13. Configuration & Deployment")

    pdf.section_title("Environment Variables (.env)")
    env_vars = [
        ("DATABASE_URL", "PostgreSQL connection string"),
        ("JWT_SECRET", "JWT signing secret"),
        ("JWT_ALGORITHM", "HS256"),
        ("JWT_EXPIRY_MINUTES", "Token expiry (480 = 8 hours)"),
        ("OPENAI_API_KEY", "OpenAI API key for all AI features"),
        ("LLM_MODEL", "gpt-4o-mini"),
        ("SMTP_HOST/PORT/USER/PASSWORD", "Gmail SMTP for emails"),
        ("GOOGLE_CLIENT_ID/SECRET", "Google OAuth credentials"),
        ("GOOGLE_REDIRECT_URI", "OAuth callback URL"),
        ("GOOGLE_DRIVE_REFRESH_TOKEN", "Drive API access"),
        ("MONGO_URL/DB", "MongoDB connection for chat"),
        ("PUBLIC_REGISTER_KEY", "API key for Google Form endpoint"),
    ]
    w = [65, 125]
    pdf.table_header(["Variable", "Purpose"], w)
    for i, (var, purpose) in enumerate(env_vars):
        pdf.table_row([var, purpose], w, fill=i % 2 == 0)

    pdf.ln(5)
    pdf.section_title("How to Run")
    steps = [
        "1. Clone: git clone github.com/gujjulassr/hms_3.git",
        "2. Setup: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt",
        "3. Database: createdb hms_3 (PostgreSQL) + start MongoDB",
        "4. Configure: cp .env.example .env (add your keys)",
        "5. Backend: python main.py (FastAPI on port 8000)",
        "6. Seed data: bash seed_api.sh",
        "7. Frontend: streamlit run streamlit_app/app.py (port 8501)",
        "8. Tests: bash test_cases.sh (81 E2E) + pytest tests/ (67 unit)",
    ]
    for step in steps:
        pdf.bullet(step)

    # Save
    output_path = os.path.join(os.path.dirname(__file__), "docs", "HMS3_Project_Report.pdf")
    pdf.output(output_path)
    print(f"PDF generated: {output_path}")
    print(f"Pages: {pdf.page_no()}")
    return output_path


if __name__ == "__main__":
    generate_report()
