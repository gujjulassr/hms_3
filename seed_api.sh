#!/bin/bash
# Seed HMS 3 via the API so password hashing matches the running server
API="http://localhost:8000"

echo "=== Registering Doctors ==="
curl -s -X POST "$API/api/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"dr.sharma@hms.com","password":"password123","full_name":"Dr. Anita Sharma","phone":"9100000001","role":"doctor","specialization":"General Medicine"}'
echo ""
curl -s -X POST "$API/api/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"dr.patel@hms.com","password":"password123","full_name":"Dr. Rajesh Patel","phone":"9100000002","role":"doctor","specialization":"Cardiology"}'
echo ""
curl -s -X POST "$API/api/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"dr.khan@hms.com","password":"password123","full_name":"Dr. Farah Khan","phone":"9100000003","role":"doctor","specialization":"Pediatrics"}'
echo ""

echo "=== Registering Admin ==="
curl -s -X POST "$API/api/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"admin@hms.com","password":"password123","full_name":"Admin User","phone":"9000000000","role":"admin"}'
echo ""

echo "=== Registering Nurse & Staff ==="
curl -s -X POST "$API/api/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"nurse.priya@hms.com","password":"password123","full_name":"Priya Nair","phone":"9200000001","role":"nurse"}'
echo ""
curl -s -X POST "$API/api/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"staff.ravi@hms.com","password":"password123","full_name":"Ravi Kumar","phone":"9200000002","role":"staff"}'
echo ""

echo "=== Registering Patients ==="
curl -s -X POST "$API/api/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"amit@example.com","password":"password123","full_name":"Amit Verma","phone":"9300000001","role":"patient","gender":"Male","blood_group":"B+"}'
echo ""
curl -s -X POST "$API/api/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"sneha@example.com","password":"password123","full_name":"Sneha Iyer","phone":"9300000002","role":"patient","gender":"Female","blood_group":"O+"}'
echo ""
curl -s -X POST "$API/api/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"rahul@example.com","password":"password123","full_name":"Rahul Singh","phone":"9300000003","role":"patient","gender":"Male","blood_group":"A-"}'
echo ""
curl -s -X POST "$API/api/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"priyar@example.com","password":"password123","full_name":"Priya Reddy","phone":"9300000004","role":"patient","gender":"Female","blood_group":"AB+"}'
echo ""
curl -s -X POST "$API/api/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"arjun@example.com","password":"password123","full_name":"Arjun Das","phone":"9300000005","role":"patient","gender":"Male","blood_group":"O-"}'
echo ""
curl -s -X POST "$API/api/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"meera@example.com","password":"password123","full_name":"Meera Joshi","phone":"9300000006","role":"patient","gender":"Female","blood_group":"A+"}'
echo ""
curl -s -X POST "$API/api/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"vikram@example.com","password":"password123","full_name":"Vikram Malhotra","phone":"9300000007","role":"patient","gender":"Male","blood_group":"B-"}'
echo ""
curl -s -X POST "$API/api/auth/register" -H "Content-Type: application/json" \
  -d '{"email":"ananya@example.com","password":"password123","full_name":"Ananya Pillai","phone":"9300000008","role":"patient","gender":"Female","blood_group":"O+"}'
echo ""

echo "=== Testing Login ==="
curl -s -X POST "$API/api/auth/login" -H "Content-Type: application/json" \
  -d '{"email":"amit@example.com","password":"password123"}'
echo ""

echo ""
echo "=== DONE ==="
