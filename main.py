"""
HMS 3 — Hospital Management System
FastAPI backend with LangGraph multi-agent chatbot.
Run: python main.py
"""
import asyncio
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from config.database import engine
from models.base import Base
from models import user, patient, doctor, session, appointment, audit_log, beneficiary, rating, report  # noqa: F401
from services.scheduler import scheduler_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: create tables + start scheduler
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[STARTUP] Database tables created.")

    # Start background scheduler
    task = asyncio.create_task(scheduler_loop())
    print("[STARTUP] Background scheduler started.")

    yield

    # Shutdown
    task.cancel()
    print("[SHUTDOWN] Scheduler stopped.")


app = FastAPI(title="HMS 3", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Import and register routes
from api.routes.auth import router as auth_router
from api.routes.doctor_dashboard import router as doctor_router
from api.routes.chat import router as chat_router
from api.routes.appointments import router as appointments_router
from api.routes.analytics import router as analytics_router
from api.routes.admin import router as admin_router

app.include_router(auth_router)
app.include_router(doctor_router)
app.include_router(chat_router)
app.include_router(appointments_router)
app.include_router(analytics_router)
app.include_router(admin_router)


@app.get("/")
async def root():
    return {"message": "HMS 3 API is running"}


@app.get("/health")
async def health():
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
