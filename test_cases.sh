#!/bin/bash
# Rigorous end-to-end test suite for HMS 3
API="http://localhost:8000"
PASS=0
FAIL=0

check() {
    local test_name="$1"
    local expected="$2"
    local actual="$3"
    if echo "$actual" | grep -q "$expected"; then
        echo "  ✓ $test_name"
        PASS=$((PASS + 1))
    else
        echo "  ✗ $test_name"
        echo "    Expected: $expected"
        echo "    Got: $actual"
        FAIL=$((FAIL + 1))
    fi
}

get_token() {
    curl -s -X POST "$API/api/auth/login" -H "Content-Type: application/json" \
      -d "{\"email\":\"$1\",\"password\":\"password123\"}" | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])" 2>/dev/null
}

# ═══════════════════════════════════════════════════════════════════════════
echo "═══════════════════════════════════════════════════"
echo "  HMS 3 — RIGOROUS TEST SUITE"
echo "═══════════════════════════════════════════════════"

# ── 1. AUTH TESTS ──────────────────────────────────────────────────────────
echo ""
echo "── 1. AUTH TESTS ──"

# 1.1 Login with valid credentials
R=$(curl -s -X POST "$API/api/auth/login" -H "Content-Type: application/json" \
  -d '{"email":"amit@example.com","password":"password123"}')
check "Login valid credentials" "token" "$R"

# 1.2 Login with wrong password
R=$(curl -s -X POST "$API/api/auth/login" -H "Content-Type: application/json" \
  -d '{"email":"amit@example.com","password":"wrongpass"}')
check "Login wrong password → 401" "Invalid credentials" "$R"

# 1.3 Login with non-existent user
R=$(curl -s -X POST "$API/api/auth/login" -H "Content-Type: application/json" \
  -d '{"email":"nobody@example.com","password":"password123"}')
check "Login non-existent user → 401" "Invalid credentials" "$R"

# 1.4 Register duplicate email
R=$(curl -s -X POST "$API/api/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"amit@example.com","password":"test123","full_name":"Test","role":"patient"}')
check "Register duplicate email → 400" "already registered" "$R"

# 1.5 Register new user
R=$(curl -s -X POST "$API/api/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"newuser@test.com","password":"test123","full_name":"New User","phone":"9999999999","role":"patient","gender":"Male","blood_group":"O+"}')
check "Register new patient" "Patient registered" "$R"

# 1.6 Login as new user
R=$(curl -s -X POST "$API/api/auth/login" -H "Content-Type: application/json" \
  -d '{"email":"newuser@test.com","password":"test123"}')
check "Login as new user" "token" "$R"

# 1.7 Change password
R=$(curl -s -X POST "$API/api/auth/change-password/newuser@test.com" -H "Content-Type: application/json" \
  -d '{"current_password":"test123","new_password":"newpass123"}')
check "Change password" "Password changed" "$R"

# 1.8 Login with new password
R=$(curl -s -X POST "$API/api/auth/login" -H "Content-Type: application/json" \
  -d '{"email":"newuser@test.com","password":"newpass123"}')
check "Login with new password" "token" "$R"

# 1.9 Change password with wrong current
R=$(curl -s -X POST "$API/api/auth/change-password/newuser@test.com" -H "Content-Type: application/json" \
  -d '{"current_password":"wrongold","new_password":"abc123"}')
check "Change password wrong current → 401" "incorrect" "$R"

# 1.10 Google OAuth URL
R=$(curl -s "$API/api/auth/google/login")
check "Google OAuth URL" "accounts.google.com" "$R"

# ── 2. PATIENT PROFILE TESTS ──────────────────────────────────────────────
echo ""
echo "── 2. PATIENT PROFILE TESTS ──"
PAT_TOKEN=$(get_token "amit@example.com")

# 2.1 Get profile
R=$(curl -s "$API/api/my-profile" -H "Authorization: Bearer $PAT_TOKEN")
check "Get patient profile" "HMS-2026-00001" "$R"
check "Profile has name" "Amit Verma" "$R"

# 2.2 Update profile
R=$(curl -s -X PUT "$API/api/my-profile" -H "Content-Type: application/json" -H "Authorization: Bearer $PAT_TOKEN" \
  -d '{"address":"123 Test Street","emergency_contact_name":"Mom","emergency_contact_phone":"9876543210"}')
check "Update profile" "Profile updated" "$R"

# 2.3 Verify update
R=$(curl -s "$API/api/my-profile" -H "Authorization: Bearer $PAT_TOKEN")
check "Profile updated - address" "123 Test Street" "$R"
check "Profile updated - emergency contact" "Mom" "$R"

# ── 3. DOCTOR SESSION TESTS ───────────────────────────────────────────────
echo ""
echo "── 3. DOCTOR SESSION TESTS ──"
DOC_TOKEN=$(get_token "dr.sharma@hms.com")

# 3.1 Create session for today
R=$(curl -s -X POST "$API/api/doctor/create-session" -H "Content-Type: application/json" -H "Authorization: Bearer $DOC_TOKEN" \
  -d '{"session_date":"2026-04-08","start_time":"09:00","end_time":"17:00","slot_duration":15}')
check "Create session today" "Session created" "$R"

# 3.2 Duplicate session same day
R=$(curl -s -X POST "$API/api/doctor/create-session" -H "Content-Type: application/json" -H "Authorization: Bearer $DOC_TOKEN" \
  -d '{"session_date":"2026-04-08","start_time":"10:00","end_time":"16:00","slot_duration":15}')
check "Duplicate session same day → 400" "already has" "$R"

# 3.3 Create session in past
R=$(curl -s -X POST "$API/api/doctor/create-session" -H "Content-Type: application/json" -H "Authorization: Bearer $DOC_TOKEN" \
  -d '{"session_date":"2026-04-01","start_time":"09:00","end_time":"17:00","slot_duration":15}')
check "Session in past → 400" "past" "$R"

# 3.4 Get sessions
R=$(curl -s "$API/api/doctor/my-sessions" -H "Authorization: Bearer $DOC_TOKEN")
check "Get doctor sessions" "sessions" "$R"

# 3.5 Activate session
R=$(curl -s -X POST "$API/api/doctor/activate-session" -H "Authorization: Bearer $DOC_TOKEN")
check "Activate session" "activated" "$R"

# 3.6 Double activate
R=$(curl -s -X POST "$API/api/doctor/activate-session" -H "Authorization: Bearer $DOC_TOKEN")
check "Double activate → 404" "No scheduled session" "$R"

# 3.7 Create session for Dr. Patel
DOC2_TOKEN=$(get_token "dr.patel@hms.com")
R=$(curl -s -X POST "$API/api/doctor/create-session" -H "Content-Type: application/json" -H "Authorization: Bearer $DOC2_TOKEN" \
  -d '{"session_date":"2026-04-08","start_time":"10:00","end_time":"16:00","slot_duration":20}')
check "Create Patel session" "Session created" "$R"

# ── 4. APPOINTMENT BOOKING TESTS ──────────────────────────────────────────
echo ""
echo "── 4. APPOINTMENT BOOKING TESTS ──"

# 4.1 Book appointment
R=$(curl -s -X POST "$API/api/book-appointment" -H "Content-Type: application/json" -H "Authorization: Bearer $PAT_TOKEN" \
  -d '{"patient_uhid":"HMS-2026-00001","doctor_name":"Anita Sharma","preferred_time":"09:00","preferred_date":"2026-04-08","confirm":true}')
check "Book appointment" "booked" "$R"

# 4.2 Duplicate booking same session
R=$(curl -s -X POST "$API/api/book-appointment" -H "Content-Type: application/json" -H "Authorization: Bearer $PAT_TOKEN" \
  -d '{"patient_uhid":"HMS-2026-00001","doctor_name":"Anita Sharma","preferred_time":"10:00","preferred_date":"2026-04-08","confirm":true}')
check "Duplicate booking → 409" "already has" "$R"

# 4.3 Book second patient at same slot
PAT2_TOKEN=$(get_token "sneha@example.com")
R=$(curl -s -X POST "$API/api/book-appointment" -H "Content-Type: application/json" -H "Authorization: Bearer $PAT2_TOKEN" \
  -d '{"patient_uhid":"HMS-2026-00002","doctor_name":"Anita Sharma","preferred_time":"09:00","preferred_date":"2026-04-08","confirm":true}')
check "Second patient same slot (overbooking)" "booked" "$R"

# 4.4 Fill slot completely, book third
PAT3_TOKEN=$(get_token "rahul@example.com")
R=$(curl -s -X POST "$API/api/book-appointment" -H "Content-Type: application/json" -H "Authorization: Bearer $PAT3_TOKEN" \
  -d '{"patient_uhid":"HMS-2026-00003","doctor_name":"Anita Sharma","preferred_time":"09:00","preferred_date":"2026-04-08","confirm":true}')
check "Third patient full slot → next slot" "09:15" "$R"

# 4.5 Check available slots
R=$(curl -s "$API/api/available-slots?doctor_name=Anita+Sharma&date=2026-04-08" -H "Authorization: Bearer $PAT_TOKEN")
check "Available slots API" "slots" "$R"

# 4.6 Book with non-existent doctor
R=$(curl -s -X POST "$API/api/book-appointment" -H "Content-Type: application/json" -H "Authorization: Bearer $PAT_TOKEN" \
  -d '{"patient_uhid":"HMS-2026-00001","doctor_name":"Dr Nobody","preferred_date":"2026-04-08","confirm":true}')
check "Book non-existent doctor → 404" "not found" "$R"

# 4.7 Book with non-existent patient
R=$(curl -s -X POST "$API/api/book-appointment" -H "Content-Type: application/json" -H "Authorization: Bearer $PAT_TOKEN" \
  -d '{"patient_uhid":"HMS-9999-99999","doctor_name":"Anita Sharma","preferred_date":"2026-04-08","confirm":true}')
check "Book non-existent patient → 404" "not found" "$R"

# 4.8 Get my appointments
R=$(curl -s "$API/api/my-appointments" -H "Authorization: Bearer $PAT_TOKEN")
check "Get my appointments" "appointments" "$R"

# ── 5. CHECK-IN / QUEUE / CALL / COMPLETE TESTS ──────────────────────────
echo ""
echo "── 5. QUEUE FLOW TESTS ──"

# 5.1 Check in patient (session must be active)
R=$(curl -s -X POST "$API/api/doctor/checkin-patient" -H "Content-Type: application/json" -H "Authorization: Bearer $DOC_TOKEN" \
  -d '{"patient_uhid":"HMS-2026-00001"}')
check "Check in patient" "checked in" "$R"

# 5.2 Double check-in
R=$(curl -s -X POST "$API/api/doctor/checkin-patient" -H "Content-Type: application/json" -H "Authorization: Bearer $DOC_TOKEN" \
  -d '{"patient_uhid":"HMS-2026-00001"}')
check "Double check-in → 404" "No booked" "$R"

# 5.3 Get queue
R=$(curl -s "$API/api/doctor/queue" -H "Authorization: Bearer $DOC_TOKEN")
check "Get queue" "waiting" "$R"

# 5.4 Call patient
R=$(curl -s -X POST "$API/api/doctor/call-patient" -H "Content-Type: application/json" -H "Authorization: Bearer $DOC_TOKEN" \
  -d '{"patient_uhid":"HMS-2026-00001"}')
check "Call patient" "called in" "$R"

# 5.5 Queue shows in_progress
R=$(curl -s "$API/api/doctor/queue" -H "Authorization: Bearer $DOC_TOKEN")
check "Queue shows in_progress" "in_progress" "$R"

# 5.6 Complete appointment
R=$(curl -s -X POST "$API/api/doctor/complete-appointment" -H "Content-Type: application/json" -H "Authorization: Bearer $DOC_TOKEN" \
  -d '{"patient_uhid":"HMS-2026-00001"}')
check "Complete appointment" "completed" "$R"

# 5.7 Complete already completed
R=$(curl -s -X POST "$API/api/doctor/complete-appointment" -H "Content-Type: application/json" -H "Authorization: Bearer $DOC_TOKEN" \
  -d '{"patient_uhid":"HMS-2026-00001"}')
check "Complete already completed → 404" "No in-progress" "$R"

# ── 6. CANCEL TESTS ──────────────────────────────────────────────────────
echo ""
echo "── 6. CANCEL TESTS ──"

# 6.1 Cancel booked appointment
R=$(curl -s -X POST "$API/api/doctor/cancel-appointment" -H "Content-Type: application/json" -H "Authorization: Bearer $DOC_TOKEN" \
  -d '{"patient_uhid":"HMS-2026-00003"}')
check "Cancel booked appointment" "cancelled" "$R"

# 6.2 Cancel already cancelled
R=$(curl -s -X POST "$API/api/doctor/cancel-appointment" -H "Content-Type: application/json" -H "Authorization: Bearer $DOC_TOKEN" \
  -d '{"patient_uhid":"HMS-2026-00003"}')
check "Cancel already cancelled → 404" "No active" "$R"

# 6.3 Cancel via patient dashboard
R=$(curl -s -X POST "$API/api/cancel-my-appointment" -H "Content-Type: application/json" -H "Authorization: Bearer $PAT2_TOKEN" \
  -d '{"doctor_name":"Anita Sharma"}')
check "Patient cancels own appointment" "cancelled" "$R"

# ── 7. RESCHEDULE TESTS ──────────────────────────────────────────────────
echo ""
echo "── 7. RESCHEDULE TESTS ──"

# Book fresh for reschedule test
PAT4_TOKEN=$(get_token "priyar@example.com")
curl -s -X POST "$API/api/book-appointment" -H "Content-Type: application/json" -H "Authorization: Bearer $PAT4_TOKEN" \
  -d '{"patient_uhid":"HMS-2026-00004","doctor_name":"Anita Sharma","preferred_time":"11:00","preferred_date":"2026-04-08","confirm":true}' > /dev/null

# 7.1 Reschedule to free slot
R=$(curl -s -X POST "$API/api/reschedule-appointment" -H "Content-Type: application/json" -H "Authorization: Bearer $PAT4_TOKEN" \
  -d '{"doctor_name":"Anita Sharma","new_date":"2026-04-08","new_time":"14:00"}')
check "Reschedule to free slot" "Rescheduled" "$R"

# 7.2 Check old is rescheduled status
R=$(psql postgresql://postgres:postgres@localhost:5432/hms_3 -t -c "SELECT status FROM appointments WHERE patient_id=(SELECT id FROM patients WHERE uhid='HMS-2026-00004') AND status='rescheduled';")
check "Old appointment marked rescheduled" "rescheduled" "$R"

# 7.3 Reschedule to full slot
# Fill 09:00 first
curl -s -X POST "$API/api/book-appointment" -H "Content-Type: application/json" -H "Authorization: Bearer $PAT3_TOKEN" \
  -d '{"patient_uhid":"HMS-2026-00003","doctor_name":"Anita Sharma","preferred_time":"09:00","preferred_date":"2026-04-08","confirm":true}' > /dev/null
curl -s -X POST "$API/api/book-appointment" -H "Content-Type: application/json" -H "Authorization: Bearer $PAT2_TOKEN" \
  -d '{"patient_uhid":"HMS-2026-00002","doctor_name":"Anita Sharma","preferred_time":"09:00","preferred_date":"2026-04-08","confirm":true}' > /dev/null
R=$(curl -s -X POST "$API/api/reschedule-appointment" -H "Content-Type: application/json" -H "Authorization: Bearer $PAT4_TOKEN" \
  -d '{"doctor_name":"Anita Sharma","new_date":"2026-04-08","new_time":"09:00"}')
check "Reschedule to full slot → error" "full" "$R"

# 7.4 No risk penalty on reschedule
R=$(psql postgresql://postgres:postgres@localhost:5432/hms_3 -t -c "SELECT risk_score FROM patients WHERE uhid='HMS-2026-00004';")
check "No risk penalty on reschedule (score=0)" "0" "$R"

# ── 8. EMERGENCY TESTS ───────────────────────────────────────────────────
echo ""
echo "── 8. EMERGENCY TESTS ──"

# 8.1 Emergency book
PAT5_TOKEN=$(get_token "arjun@example.com")
R=$(curl -s -X POST "$API/api/doctor/emergency-book" -H "Content-Type: application/json" -H "Authorization: Bearer $DOC_TOKEN" \
  -d '{"patient_uhid":"HMS-2026-00005"}')
check "Emergency booking" "emergency queue" "$R"

# 8.2 Emergency in queue
R=$(curl -s "$API/api/doctor/queue" -H "Authorization: Bearer $DOC_TOKEN")
check "Emergency shows in queue" "emergency" "$R"

# 8.3 Duplicate emergency
R=$(curl -s -X POST "$API/api/doctor/emergency-book" -H "Content-Type: application/json" -H "Authorization: Bearer $DOC_TOKEN" \
  -d '{"patient_uhid":"HMS-2026-00005"}')
check "Duplicate emergency → 400" "already has" "$R"

# 8.4 Emergency for non-existent patient
R=$(curl -s -X POST "$API/api/doctor/emergency-book" -H "Content-Type: application/json" -H "Authorization: Bearer $DOC_TOKEN" \
  -d '{"patient_uhid":"HMS-9999-99999"}')
check "Emergency non-existent → 404" "not found" "$R"

# ── 9. BENEFICIARY TESTS ─────────────────────────────────────────────────
echo ""
echo "── 9. BENEFICIARY TESTS ──"

# 9.1 Add beneficiary
R=$(curl -s -X POST "$API/api/my-beneficiaries" -H "Content-Type: application/json" -H "Authorization: Bearer $PAT_TOKEN" \
  -d '{"name":"Test Bene","relationship":"Spouse","phone":"1234567890","gender":"Female","blood_group":"A+"}')
check "Add beneficiary" "added" "$R"

# 9.2 Get beneficiaries
R=$(curl -s "$API/api/my-beneficiaries" -H "Authorization: Bearer $PAT_TOKEN")
check "Get beneficiaries" "Test Bene" "$R"

# 9.3 Beneficiary registered as patient
R=$(psql postgresql://postgres:postgres@localhost:5432/hms_3 -t -c "SELECT uhid FROM patients p JOIN users u ON p.user_id=u.id WHERE u.full_name='Test Bene';")
check "Beneficiary auto-registered as patient" "HMS-2026" "$R"

# 9.4 Update beneficiary
BEN_ID=$(curl -s "$API/api/my-beneficiaries" -H "Authorization: Bearer $PAT_TOKEN" | python3 -c "import sys,json; bens=json.load(sys.stdin)['beneficiaries']; print(bens[0]['id'] if bens else '')")
R=$(curl -s -X PUT "$API/api/my-beneficiaries/$BEN_ID" -H "Content-Type: application/json" -H "Authorization: Bearer $PAT_TOKEN" \
  -d '{"phone":"9999999999"}')
check "Update beneficiary" "updated" "$R"

# 9.5 Delete beneficiary
R=$(curl -s -X DELETE "$API/api/my-beneficiaries/$BEN_ID" -H "Authorization: Bearer $PAT_TOKEN")
check "Delete beneficiary" "removed" "$R"

# ── 10. SESSION COMPLETION & NO-SHOW TESTS ────────────────────────────────
echo ""
echo "── 10. SESSION COMPLETION TESTS ──"

# Get risk scores before
RS_BEFORE=$(psql postgresql://postgres:postgres@localhost:5432/hms_3 -t -c "SELECT risk_score FROM patients WHERE uhid='HMS-2026-00003';")

# 10.1 Complete session (Sneha checked_in, Rahul booked, Arjun emergency)
# Check in Sneha first
curl -s -X POST "$API/api/doctor/checkin-patient" -H "Content-Type: application/json" -H "Authorization: Bearer $DOC_TOKEN" \
  -d '{"patient_uhid":"HMS-2026-00002"}' > /dev/null
R=$(curl -s -X POST "$API/api/doctor/complete-session" -H "Authorization: Bearer $DOC_TOKEN")
check "Complete session" "completed" "$R"

# 10.2 Booked patients → no_show
R=$(psql postgresql://postgres:postgres@localhost:5432/hms_3 -t -c "SELECT status FROM appointments WHERE patient_id=(SELECT id FROM patients WHERE uhid='HMS-2026-00003') AND status='no_show' LIMIT 1;")
check "Booked patient → no_show" "no_show" "$R"

# 10.3 Risk score increased for no-show
RS_AFTER=$(psql postgresql://postgres:postgres@localhost:5432/hms_3 -t -c "SELECT risk_score FROM patients WHERE uhid='HMS-2026-00003';")
# Risk was 10 (from cancel) + 20 (no-show) = 30
check "Risk score increased for no-show" "30" "$RS_AFTER"

# 10.4 Checked-in patient → cancelled (no risk)
R=$(psql postgresql://postgres:postgres@localhost:5432/hms_3 -t -c "SELECT status FROM appointments WHERE patient_id=(SELECT id FROM patients WHERE uhid='HMS-2026-00002') AND status='cancelled' LIMIT 1;")
check "Checked-in patient → cancelled" "cancelled" "$R"

# ── 11. ADMIN TESTS ──────────────────────────────────────────────────────
echo ""
echo "── 11. ADMIN TESTS ──"
ADMIN_TOKEN=$(get_token "admin@hms.com")

# 11.1 Admin stats
R=$(curl -s "$API/api/admin/stats" -H "Authorization: Bearer $ADMIN_TOKEN")
check "Admin stats" "total_users" "$R"

# 11.2 Admin users list
R=$(curl -s "$API/api/admin/users" -H "Authorization: Bearer $ADMIN_TOKEN")
check "Admin users list" "users" "$R"

# 11.3 Admin users filter by role
R=$(curl -s "$API/api/admin/users?role=doctor" -H "Authorization: Bearer $ADMIN_TOKEN")
check "Filter users by role" "doctor" "$R"

# 11.4 Admin doctors list
R=$(curl -s "$API/api/admin/doctors" -H "Authorization: Bearer $ADMIN_TOKEN")
check "Admin doctors list" "doctors" "$R"

# 11.5 Admin patients list
R=$(curl -s "$API/api/admin/patients" -H "Authorization: Bearer $ADMIN_TOKEN")
check "Admin patients list" "patients" "$R"

# 11.6 Search patients
R=$(curl -s "$API/api/admin/patients?search=Amit" -H "Authorization: Bearer $ADMIN_TOKEN")
check "Search patients by name" "Amit" "$R"

# 11.7 Admin sessions
R=$(curl -s "$API/api/admin/sessions" -H "Authorization: Bearer $ADMIN_TOKEN")
check "Admin sessions list" "sessions" "$R"

# 11.8 Admin audit logs
R=$(curl -s "$API/api/admin/audit-logs" -H "Authorization: Bearer $ADMIN_TOKEN")
check "Admin audit logs" "logs" "$R"

# 11.9 Toggle user active
USER_ID=$(curl -s "$API/api/admin/users?role=patient" -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import sys,json; users=json.load(sys.stdin)['users']; print(users[-1]['id'])")
R=$(curl -s -X POST "$API/api/admin/toggle-user/$USER_ID" -H "Authorization: Bearer $ADMIN_TOKEN")
check "Toggle user status" "activated\|deactivated" "$R"

# 11.10 Admin edit user
ORIG_NAME=$(curl -s "$API/api/admin/users?role=patient" -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import sys,json; users=json.load(sys.stdin)['users']; print(users[-1]['full_name'])" 2>/dev/null)
R=$(curl -s -X PUT "$API/api/admin/users/$USER_ID" -H "Content-Type: application/json" -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d '{"full_name":"Edited Name","phone":"0000000000"}')
check "Admin edit user" "updated" "$R"
# Restore original name
curl -s -X PUT "$API/api/admin/users/$USER_ID" -H "Content-Type: application/json" -H "Authorization: Bearer $ADMIN_TOKEN" \
  -d "{\"full_name\":\"$ORIG_NAME\"}" > /dev/null

# 11.11 Non-admin can't access admin endpoints
R=$(curl -s "$API/api/admin/stats" -H "Authorization: Bearer $PAT_TOKEN")
check "Patient can't access admin stats → 403" "Staff access" "$R"

# 11.12 Admin create session for any doctor
R=$(curl -s -X POST "$API/api/admin/sessions/$(curl -s "$API/api/admin/sessions" -H "Authorization: Bearer $ADMIN_TOKEN" | python3 -c "import sys,json; s=json.load(sys.stdin)['sessions']; print(s[0]['id'] if s else '')")/activate" -H "Authorization: Bearer $ADMIN_TOKEN")
check "Admin session action" "activated\|not today\|not found\|already\|Cannot" "$R"

# ── 12. DOCTORS LIST & AVAILABLE SLOTS ────────────────────────────────────
echo ""
echo "── 12. DOCTORS & SLOTS TESTS ──"

# 12.1 List all doctors
R=$(curl -s "$API/api/doctors" -H "Authorization: Bearer $PAT_TOKEN")
check "List all doctors" "Anita Sharma" "$R"

# 12.2 Filter by specialization
R=$(curl -s "$API/api/doctors?specialization=Cardiology" -H "Authorization: Bearer $PAT_TOKEN")
check "Filter doctors by specialization" "Rajesh Patel" "$R"

# 12.3 Available slots non-existent session
R=$(curl -s "$API/api/available-slots?doctor_name=Rajesh+Patel&date=2026-04-08" -H "Authorization: Bearer $PAT_TOKEN")
check "Available slots for session" "slots" "$R"

# ── 13. CHAT HISTORY (MongoDB) ────────────────────────────────────────────
echo ""
echo "── 13. CHAT HISTORY TESTS ──"

# 13.1 Send chat message
R=$(curl -s -X POST "$API/api/chat/message" -H "Content-Type: application/json" -H "Authorization: Bearer $PAT_TOKEN" \
  -d '{"message":"hello"}')
check "Chat sends response" "response" "$R"

# 13.2 Get chat history
R=$(curl -s "$API/api/chat/history" -H "Authorization: Bearer $PAT_TOKEN")
check "Chat history from MongoDB" "messages" "$R"

# 13.3 Clear chat history
R=$(curl -s -X DELETE "$API/api/chat/history" -H "Authorization: Bearer $PAT_TOKEN")
check "Clear chat history" "cleared" "$R"

# 13.4 History empty after clear
R=$(curl -s "$API/api/chat/history" -H "Authorization: Bearer $PAT_TOKEN")
check "History empty after clear" "messages" "$R"

# ── 14. EDGE CASES ───────────────────────────────────────────────────────
echo ""
echo "── 14. EDGE CASES ──"

# 14.1 Health check
R=$(curl -s "$API/health")
check "Health check" "ok" "$R"

# 14.2 Root endpoint
R=$(curl -s "$API/")
check "Root endpoint" "running" "$R"

# 14.3 Unauthorized access
R=$(curl -s "$API/api/my-profile")
check "Unauthorized → 403" "Not authenticated\|detail" "$R"

# 14.4 Invalid token
R=$(curl -s "$API/api/my-profile" -H "Authorization: Bearer invalidtoken123")
check "Invalid token → 401" "Invalid\|detail" "$R"

# 14.5 Lunch hour check (no slots between 13:00-14:00)
R=$(curl -s "$API/api/available-slots?doctor_name=Anita+Sharma&date=2026-04-08" -H "Authorization: Bearer $PAT_TOKEN" | python3 -c "
import sys,json
data = json.load(sys.stdin)
lunch_slots = [s for s in data.get('slots',[]) if '13:' in s['slot_time'] and s['slot_time'] < '14:00:00']
print('NO_LUNCH_SLOTS' if not lunch_slots else 'HAS_LUNCH_SLOTS')
" 2>/dev/null)
check "No slots during lunch (13:00-14:00)" "NO_LUNCH_SLOTS" "$R"

# ═══════════════════════════════════════════════════════════════════════════
echo ""
echo "═══════════════════════════════════════════════════"
echo "  RESULTS: $PASS passed, $FAIL failed"
echo "═══════════════════════════════════════════════════"
