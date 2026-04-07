# HMS 3 — Sample Dataset

## How to Load
```bash
# 1. Create database
createdb hms_3

# 2. Start backend (creates tables)
python main.py

# 3. Seed data via API
bash seed_api.sh
```

## Sample Users

### Admin
| Email | Password | Role |
|-------|----------|------|
| admin@hms.com | password123 | admin |

### Doctors
| Email | Password | Name | Specialization |
|-------|----------|------|----------------|
| dr.sharma@hms.com | password123 | Dr. Anita Sharma | General Medicine |
| dr.patel@hms.com | password123 | Dr. Rajesh Patel | Cardiology |
| dr.khan@hms.com | password123 | Dr. Farah Khan | Pediatrics |

### Staff
| Email | Password | Name | Role |
|-------|----------|------|------|
| nurse.priya@hms.com | password123 | Priya Nair | nurse |
| staff.ravi@hms.com | password123 | Ravi Kumar | staff |

### Patients
| Email | Password | Name | UHID | Gender | Blood Group |
|-------|----------|------|------|--------|-------------|
| amit@example.com | password123 | Amit Verma | HMS-2026-00001 | Male | B+ |
| sneha@example.com | password123 | Sneha Iyer | HMS-2026-00002 | Female | O+ |
| rahul@example.com | password123 | Rahul Singh | HMS-2026-00003 | Male | A- |
| priyar@example.com | password123 | Priya Reddy | HMS-2026-00004 | Female | AB+ |
| arjun@example.com | password123 | Arjun Das | HMS-2026-00005 | Male | O- |
| meera@example.com | password123 | Meera Joshi | HMS-2026-00006 | Female | A+ |
| vikram@example.com | password123 | Vikram Malhotra | HMS-2026-00007 | Male | B- |
| ananya@example.com | password123 | Ananya Pillai | HMS-2026-00008 | Female | O+ |

## Database Schema

### Tables
- **users** — All system users (patients, doctors, admin, staff, nurse)
- **patients** — Patient-specific data (UHID, gender, blood group, risk score)
- **doctors** — Doctor-specific data (specialization, max patients/day)
- **sessions** — Doctor daily sessions (date, time, slots, lunch break)
- **appointments** — Patient appointments (slot, status, priority, timestamps)
- **beneficiaries** — Patient family members (also registered as patients)
- **audit_logs** — All system actions with actor and details
- **ratings** — Patient feedback/ratings for doctors
- **consultation_reports** — LLM-generated reports (content, PDF path, Drive link)

### External Storage
- **MongoDB** — Chat message history (persistent across sessions)
- **Google Drive** — Consultation report PDFs (shareable links)
