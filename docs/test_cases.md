# HMS 3 — Test Cases Documentation

## Test Suite: 81 End-to-End Tests (test_rigorous.sh)

### 1. Authentication Tests (10 tests)
| # | Test Case | Input | Expected | Status |
|---|-----------|-------|----------|--------|
| 1.1 | Login valid credentials | email=amit@example.com, password=password123 | JWT token returned | PASS |
| 1.2 | Login wrong password | email=amit@example.com, password=wrongpass | 401 Invalid credentials | PASS |
| 1.3 | Login non-existent user | email=nobody@example.com | 401 Invalid credentials | PASS |
| 1.4 | Register duplicate email | email=amit@example.com (exists) | 400 Already registered | PASS |
| 1.5 | Register new patient | email=newuser@test.com, role=patient | 200 Patient registered with UHID | PASS |
| 1.6 | Login as new user | email=newuser@test.com | JWT token returned | PASS |
| 1.7 | Change password | current=test123, new=newpass123 | Password changed | PASS |
| 1.8 | Login with new password | password=newpass123 | JWT token returned | PASS |
| 1.9 | Change password wrong current | current=wrongold | 401 Incorrect | PASS |
| 1.10 | Google OAuth URL | GET /api/auth/google/login | URL contains accounts.google.com | PASS |

### 2. Patient Profile Tests (5 tests)
| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 2.1 | Get patient profile | Returns UHID, name, email, phone | PASS |
| 2.2 | Profile has correct name | "Amit Verma" | PASS |
| 2.3 | Update profile (address, emergency contact) | "Profile updated" | PASS |
| 2.4 | Verify address updated | "123 Test Street" | PASS |
| 2.5 | Verify emergency contact | "Mom" | PASS |

### 3. Doctor Session Tests (7 tests)
| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 3.1 | Create session for today | "Session created" with slot count | PASS |
| 3.2 | Duplicate session same day | 400 "already has" | PASS |
| 3.3 | Create session in past | 400 "past" | PASS |
| 3.4 | Get sessions list | Returns sessions array | PASS |
| 3.5 | Activate session | "activated" | PASS |
| 3.6 | Double activate | 404 "No scheduled session" | PASS |
| 3.7 | Create session for another doctor | "Session created" | PASS |

### 4. Appointment Booking Tests (8 tests)
| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 4.1 | Book appointment at specific slot | status=booked, slot_number assigned | PASS |
| 4.2 | Duplicate booking same session | 409 "already has" | PASS |
| 4.3 | Second patient same slot (overbooking) | Booked (max_per_slot=2) | PASS |
| 4.4 | Third patient full slot | Moves to next slot (09:15) | PASS |
| 4.5 | Get available slots | Returns slots with positions | PASS |
| 4.6 | Book with non-existent doctor | 404 "not found" | PASS |
| 4.7 | Book with non-existent patient | 404 "not found" | PASS |
| 4.8 | Get my appointments | Returns appointments list | PASS |

### 5. Queue Flow Tests (7 tests)
| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 5.1 | Check in patient | "checked in at HH:MM" | PASS |
| 5.2 | Double check-in | 404 "No booked" | PASS |
| 5.3 | Get queue | Returns waiting/booked/emergency lists | PASS |
| 5.4 | Call patient | "called in" | PASS |
| 5.5 | Queue shows in_progress | in_progress list populated | PASS |
| 5.6 | Complete appointment | "completed" with delay info | PASS |
| 5.7 | Complete already completed | 404 "No in-progress" | PASS |

### 6. Cancel Tests (3 tests)
| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 6.1 | Cancel booked appointment | "cancelled" + risk +10 | PASS |
| 6.2 | Cancel already cancelled | 404 "No active" | PASS |
| 6.3 | Patient cancels own appointment | "cancelled" | PASS |

### 7. Reschedule Tests (4 tests)
| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 7.1 | Reschedule to free slot | "Rescheduled" old→new | PASS |
| 7.2 | Old appointment status | status = "rescheduled" | PASS |
| 7.3 | Reschedule to full slot | 409 "full" | PASS |
| 7.4 | No risk penalty | risk_score unchanged (0) | PASS |

### 8. Emergency Tests (4 tests)
| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 8.1 | Emergency booking | "emergency queue" | PASS |
| 8.2 | Emergency in queue | Shows in emergency list | PASS |
| 8.3 | Duplicate emergency | 400 "already has" | PASS |
| 8.4 | Emergency non-existent patient | 404 "not found" | PASS |

### 9. Beneficiary Tests (5 tests)
| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 9.1 | Add beneficiary | "added" | PASS |
| 9.2 | Get beneficiaries | Returns beneficiary list | PASS |
| 9.3 | Beneficiary auto-registered as patient | Has UHID in patients table | PASS |
| 9.4 | Update beneficiary | "updated" | PASS |
| 9.5 | Delete beneficiary | "removed" | PASS |

### 10. Session Completion Tests (4 tests)
| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 10.1 | Complete session | "completed" with no-show/cancelled counts | PASS |
| 10.2 | Booked patient → no_show | status = "no_show" | PASS |
| 10.3 | Risk score +20 for no-show | risk_score increased | PASS |
| 10.4 | Checked-in → cancelled (no penalty) | status = "cancelled" | PASS |

### 11. Admin Tests (12 tests)
| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 11.1 | Admin stats | Returns total_users, patients, doctors, etc. | PASS |
| 11.2 | Admin users list | Returns all users | PASS |
| 11.3 | Filter users by role | Returns only doctors | PASS |
| 11.4 | Admin doctors list | Returns doctor details + stats | PASS |
| 11.5 | Admin patients list | Returns patient details + risk | PASS |
| 11.6 | Search patients by name | Finds "Amit" | PASS |
| 11.7 | Admin sessions list | Returns all sessions | PASS |
| 11.8 | Admin audit logs | Returns audit trail | PASS |
| 11.9 | Toggle user status | "activated/deactivated" | PASS |
| 11.10 | Admin edit user | "updated" + restores name | PASS |
| 11.11 | Patient can't access admin | 403 "Staff access" | PASS |
| 11.12 | Admin session action | Responds appropriately | PASS |

### 12. Doctors & Slots Tests (3 tests)
| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 12.1 | List all doctors | Returns all 3 doctors | PASS |
| 12.2 | Filter by specialization | Returns Cardiology doctor | PASS |
| 12.3 | Available slots for session | Returns slot list | PASS |

### 13. Chat History Tests (4 tests)
| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 13.1 | Chat sends response | Response from LLM | PASS |
| 13.2 | History from MongoDB | Messages persisted | PASS |
| 13.3 | Clear chat history | "cleared" | PASS |
| 13.4 | History empty after clear | Empty messages array | PASS |

### 14. Edge Cases (5 tests)
| # | Test Case | Expected | Status |
|---|-----------|----------|--------|
| 14.1 | Health check | {"status": "ok"} | PASS |
| 14.2 | Root endpoint | "running" | PASS |
| 14.3 | Unauthorized access | 403 | PASS |
| 14.4 | Invalid token | 401 | PASS |
| 14.5 | No slots during lunch (13:00-14:00) | No 13:xx slots | PASS |

### Unit Tests (pytest — 67 tests)
| Module | Tests | Status |
|--------|-------|--------|
| OOP (Person, Patient, Doctor) | 15 | PASS |
| ScheduleManager (binary search, slots) | 13 | PASS |
| QueueManager (priority, delay) | 11 | PASS |
| Validators (email, phone, UHID, etc.) | 15 | PASS |
| Slot Utils (generation, lunch block) | 13 | PASS |

**Total: 148 tests (81 E2E + 67 unit)**
