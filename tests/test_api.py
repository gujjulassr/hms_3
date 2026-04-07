"""
Integration tests for API routes.
Section 6: Integration tests for APIs.
Uses httpx async client with FastAPI TestClient.
"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from main import app
from config.database import engine, AsyncSessionLocal
from models.base import Base
from models.user import User
from models.patient import Patient
from models.doctor import Doctor
from models.session import Session
from passlib.context import CryptContext
import uuid
from datetime import date, time

pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create fresh tables before each test."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def auth_headers(client: AsyncClient):
    """Register and login a patient, return auth headers."""
    await client.post("/api/auth/register", json={
        "email": "test@test.com", "password": "Test1234",
        "full_name": "Test Patient", "phone": "+91-9000000001",
        "role": "patient", "gender": "Male", "blood_group": "A+"
    })
    r = await client.post("/api/auth/login", json={"email": "test@test.com", "password": "Test1234"})
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def doctor_headers(client: AsyncClient):
    """Register and login a doctor."""
    await client.post("/api/auth/register", json={
        "email": "doc@test.com", "password": "Test1234",
        "full_name": "Dr. TestDoc", "phone": "+91-9000000002",
        "role": "doctor", "specialization": "General"
    })
    r = await client.post("/api/auth/login", json={"email": "doc@test.com", "password": "Test1234"})
    token = r.json()["token"]
    return {"Authorization": f"Bearer {token}"}


class TestAuthAPI:
    @pytest.mark.asyncio
    async def test_register_patient(self, client):
        r = await client.post("/api/auth/register", json={
            "email": "new@test.com", "password": "Pass1234",
            "full_name": "New Patient", "role": "patient",
            "gender": "Female", "blood_group": "B+"
        })
        assert r.status_code == 200
        assert "UHID" in r.json()["message"]

    @pytest.mark.asyncio
    async def test_register_doctor(self, client):
        r = await client.post("/api/auth/register", json={
            "email": "newdoc@test.com", "password": "Pass1234",
            "full_name": "Dr. New", "role": "doctor",
            "specialization": "Cardiology"
        })
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_duplicate_registration(self, client):
        payload = {"email": "dup@test.com", "password": "Pass1234",
                   "full_name": "Dup User", "role": "patient"}
        await client.post("/api/auth/register", json=payload)
        r = await client.post("/api/auth/register", json=payload)
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_login_success(self, client):
        await client.post("/api/auth/register", json={
            "email": "login@test.com", "password": "Pass1234",
            "full_name": "Login User", "role": "patient"
        })
        r = await client.post("/api/auth/login", json={"email": "login@test.com", "password": "Pass1234"})
        assert r.status_code == 200
        assert "token" in r.json()

    @pytest.mark.asyncio
    async def test_login_wrong_password(self, client):
        await client.post("/api/auth/register", json={
            "email": "wrong@test.com", "password": "Pass1234",
            "full_name": "Wrong User", "role": "patient"
        })
        r = await client.post("/api/auth/login", json={"email": "wrong@test.com", "password": "WrongPass"})
        assert r.status_code == 401


class TestDoctorDashboardAPI:
    @pytest.mark.asyncio
    async def test_create_session(self, client, doctor_headers):
        r = await client.post("/api/doctor/create-session", json={
            "session_date": str(date.today()),
            "start_time": "09:00",
            "end_time": "17:00",
            "slot_duration": 15
        }, headers=doctor_headers)
        assert r.status_code == 200
        assert "created" in r.json()["message"].lower()

    @pytest.mark.asyncio
    async def test_duplicate_session(self, client, doctor_headers):
        payload = {"session_date": str(date.today()), "start_time": "09:00",
                   "end_time": "17:00", "slot_duration": 15}
        await client.post("/api/doctor/create-session", json=payload, headers=doctor_headers)
        r = await client.post("/api/doctor/create-session", json=payload, headers=doctor_headers)
        assert r.status_code == 400

    @pytest.mark.asyncio
    async def test_get_my_sessions(self, client, doctor_headers):
        await client.post("/api/doctor/create-session", json={
            "session_date": str(date.today()),
            "start_time": "09:00", "end_time": "17:00"
        }, headers=doctor_headers)
        r = await client.get("/api/doctor/my-sessions", headers=doctor_headers)
        assert r.status_code == 200
        assert len(r.json()["sessions"]) >= 1

    @pytest.mark.asyncio
    async def test_activate_session(self, client, doctor_headers):
        await client.post("/api/doctor/create-session", json={
            "session_date": str(date.today()),
            "start_time": "09:00", "end_time": "23:00"
        }, headers=doctor_headers)
        r = await client.post("/api/doctor/activate-session", headers=doctor_headers)
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_get_queue_no_session(self, client, doctor_headers):
        r = await client.get("/api/doctor/queue", headers=doctor_headers)
        assert r.status_code == 200
        assert r.json()["session"] is None


class TestAppointmentAPI:
    @pytest.mark.asyncio
    async def test_get_available_slots(self, client, auth_headers, doctor_headers):
        # Create a session first
        await client.post("/api/doctor/create-session", json={
            "session_date": str(date.today()),
            "start_time": "09:00", "end_time": "17:00"
        }, headers=doctor_headers)

        r = await client.get("/api/available-slots", params={
            "doctor_name": "TestDoc", "date": str(date.today())
        }, headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["total_available"] > 0

    @pytest.mark.asyncio
    async def test_get_appointments_empty(self, client, auth_headers):
        r = await client.get("/api/appointments", headers=auth_headers)
        assert r.status_code == 200
        assert r.json()["total"] == 0


class TestHealthEndpoints:
    @pytest.mark.asyncio
    async def test_root(self, client):
        r = await client.get("/")
        assert r.status_code == 200

    @pytest.mark.asyncio
    async def test_health(self, client):
        r = await client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
