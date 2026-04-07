"""
Data Science & Analytics — Section 7.
Busiest doctor analysis, peak booking hours prediction, visualization reports.
Uses: Pandas, NumPy, Matplotlib.

Run standalone: python -m analytics.reports
"""
import asyncio
import os
from datetime import date, datetime, timedelta
from collections import Counter

# Data science imports
import numpy as np

try:
    import pandas as pd
    HAS_PANDAS = True
except ImportError:
    HAS_PANDAS = False

try:
    import matplotlib
    matplotlib.use('Agg')  # Non-interactive backend
    import matplotlib.pyplot as plt
    import matplotlib.dates as mdates
    HAS_MATPLOTLIB = True
except ImportError:
    HAS_MATPLOTLIB = False

from sqlalchemy import select, func, and_
from config.database import AsyncSessionLocal
from models.appointment import Appointment
from models.session import Session
from models.doctor import Doctor
from models.patient import Patient
from models.user import User
from models.rating import Rating


# ─── Data Fetching ──────────────────────────────────────────────────────────

async def fetch_appointment_data(days_back: int = 30) -> list[dict]:
    """Fetch appointment data for analytics."""
    cutoff = date.today() - timedelta(days=days_back)
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Appointment, Session, Doctor, User)
            .join(Session, Appointment.session_id == Session.id)
            .join(Doctor, Session.doctor_id == Doctor.id)
            .join(User, Doctor.user_id == User.id)
            .where(Session.session_date >= cutoff)
            .order_by(Session.session_date, Appointment.slot_time)
        )
        rows = result.all()

    data = []
    for appt, session, doctor, user in rows:
        data.append({
            "appointment_id": str(appt.id),
            "doctor_name": user.full_name,
            "doctor_specialization": doctor.specialization,
            "session_date": session.session_date,
            "slot_time": appt.slot_time,
            "slot_hour": appt.slot_time.hour if appt.slot_time else 0,
            "status": appt.status,
            "priority": appt.priority,
            "is_emergency": appt.is_emergency,
            "delay_minutes": session.delay_minutes,
            "overtime_minutes": session.overtime_minutes,
        })
    return data


async def fetch_doctor_ratings() -> list[dict]:
    """Fetch all ratings with doctor info."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Rating, Doctor, User)
            .join(Doctor, Rating.doctor_id == Doctor.id)
            .join(User, Doctor.user_id == User.id)
        )
        rows = result.all()
    return [{"doctor": u.full_name, "rating": r.rating, "feedback": r.feedback,
             "date": r.created_at} for r, d, u in rows]


# ─── Analysis Functions ─────────────────────────────────────────────────────

def analyze_busiest_doctors(data: list[dict]) -> dict:
    """
    Section 7: Busiest doctor analysis using Pandas/NumPy.
    Returns: dict with rankings, stats per doctor.
    """
    if not data or not HAS_PANDAS:
        return {"error": "No data or Pandas not installed"}

    df = pd.DataFrame(data)

    # Appointments per doctor
    doctor_counts = df.groupby("doctor_name").agg(
        total_appointments=("appointment_id", "count"),
        completed=("status", lambda x: (x == "completed").sum()),
        no_shows=("status", lambda x: (x == "no_show").sum()),
        cancelled=("status", lambda x: (x == "cancelled").sum()),
        emergencies=("is_emergency", "sum"),
        avg_delay=("delay_minutes", "mean"),
    ).round(1)

    # Completion rate
    doctor_counts["completion_rate"] = (
        (doctor_counts["completed"] / doctor_counts["total_appointments"] * 100).round(1)
    )

    # Rank by total appointments
    doctor_counts = doctor_counts.sort_values("total_appointments", ascending=False)

    return {
        "rankings": doctor_counts.reset_index().to_dict("records"),
        "busiest_doctor": doctor_counts.index[0] if len(doctor_counts) > 0 else "N/A",
        "total_appointments": int(doctor_counts["total_appointments"].sum()),
        "avg_completion_rate": float(doctor_counts["completion_rate"].mean()),
    }


def analyze_peak_hours(data: list[dict]) -> dict:
    """
    Section 7: Peak booking hours prediction using NumPy.
    Returns: hourly distribution, predicted peak hours.
    """
    if not data:
        return {"error": "No data"}

    hours = [d["slot_hour"] for d in data]
    hour_counts = Counter(hours)

    # NumPy array for statistics
    counts_array = np.array([hour_counts.get(h, 0) for h in range(8, 20)])
    hours_range = list(range(8, 20))

    # Find peaks (hours above average)
    mean_count = np.mean(counts_array)
    std_count = np.std(counts_array)
    peak_threshold = mean_count + 0.5 * std_count

    peak_hours = [h for h, c in zip(hours_range, counts_array) if c >= peak_threshold]
    low_hours = [h for h, c in zip(hours_range, counts_array) if c < mean_count and c > 0]

    return {
        "hourly_distribution": {str(h): int(c) for h, c in zip(hours_range, counts_array)},
        "peak_hours": [f"{h}:00" for h in peak_hours],
        "low_hours": [f"{h}:00" for h in low_hours],
        "busiest_hour": f"{hours_range[np.argmax(counts_array)]}:00" if len(counts_array) > 0 else "N/A",
        "average_per_hour": float(round(mean_count, 1)),
        "total_analyzed": len(data),
    }


def analyze_status_distribution(data: list[dict]) -> dict:
    """Appointment status distribution analysis."""
    if not data:
        return {"error": "No data"}

    statuses = [d["status"] for d in data]
    status_counts = Counter(statuses)
    total = len(data)

    return {
        "distribution": {s: {"count": c, "percentage": round(c / total * 100, 1)}
                        for s, c in status_counts.items()},
        "total": total,
    }


def analyze_doctor_ratings(ratings: list[dict]) -> dict:
    """Doctor ratings analysis."""
    if not ratings or not HAS_PANDAS:
        return {"error": "No data or Pandas not installed"}

    df = pd.DataFrame(ratings)
    summary = df.groupby("doctor").agg(
        avg_rating=("rating", "mean"),
        total_ratings=("rating", "count"),
        min_rating=("rating", "min"),
        max_rating=("rating", "max"),
    ).round(2).sort_values("avg_rating", ascending=False)

    return {
        "ratings": summary.reset_index().to_dict("records"),
        "overall_average": float(df["rating"].mean().round(2)),
        "total_reviews": len(ratings),
    }


# ─── Visualization ──────────────────────────────────────────────────────────

def generate_charts(data: list[dict], output_dir: str = ".") -> list[str]:
    """
    Generate visualization charts as PNG files.
    Returns list of generated file paths.
    """
    if not HAS_MATPLOTLIB or not HAS_PANDAS or not data:
        return []

    df = pd.DataFrame(data)
    charts = []

    # 1. Appointments per doctor (bar chart)
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        doctor_counts = df["doctor_name"].value_counts()
        doctor_counts.plot(kind="bar", ax=ax, color=["#2196F3", "#4CAF50", "#FF9800", "#F44336"])
        ax.set_title("Appointments per Doctor", fontsize=14)
        ax.set_ylabel("Number of Appointments")
        ax.set_xlabel("Doctor")
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        path = os.path.join(output_dir, "chart_appointments_per_doctor.png")
        fig.savefig(path, dpi=100)
        plt.close(fig)
        charts.append(path)
    except Exception as e:
        print(f"Chart error: {e}")

    # 2. Peak hours (line chart)
    try:
        fig, ax = plt.subplots(figsize=(10, 6))
        hour_data = df.groupby("slot_hour").size()
        hours = range(8, 20)
        counts = [hour_data.get(h, 0) for h in hours]
        ax.plot(list(hours), counts, marker="o", linewidth=2, color="#2196F3")
        ax.fill_between(list(hours), counts, alpha=0.2, color="#2196F3")
        ax.set_title("Appointments by Hour of Day", fontsize=14)
        ax.set_ylabel("Number of Appointments")
        ax.set_xlabel("Hour")
        ax.set_xticks(list(hours))
        ax.set_xticklabels([f"{h}:00" for h in hours], rotation=45)
        ax.axhline(y=np.mean(counts), color="red", linestyle="--", label="Average")
        ax.legend()
        plt.tight_layout()
        path = os.path.join(output_dir, "chart_peak_hours.png")
        fig.savefig(path, dpi=100)
        plt.close(fig)
        charts.append(path)
    except Exception as e:
        print(f"Chart error: {e}")

    # 3. Status distribution (pie chart)
    try:
        fig, ax = plt.subplots(figsize=(8, 8))
        status_counts = df["status"].value_counts()
        colors = {"completed": "#4CAF50", "booked": "#2196F3", "checked_in": "#FF9800",
                 "cancelled": "#F44336", "no_show": "#9E9E9E", "in_progress": "#00BCD4"}
        pie_colors = [colors.get(s, "#757575") for s in status_counts.index]
        ax.pie(status_counts.values, labels=status_counts.index, autopct="%1.1f%%",
               colors=pie_colors, startangle=140)
        ax.set_title("Appointment Status Distribution", fontsize=14)
        plt.tight_layout()
        path = os.path.join(output_dir, "chart_status_distribution.png")
        fig.savefig(path, dpi=100)
        plt.close(fig)
        charts.append(path)
    except Exception as e:
        print(f"Chart error: {e}")

    # 4. Emergency vs Normal (bar chart)
    try:
        fig, ax = plt.subplots(figsize=(8, 6))
        emerg = df.groupby(["doctor_name", "is_emergency"]).size().unstack(fill_value=0)
        emerg.plot(kind="bar", ax=ax, color=["#2196F3", "#F44336"])
        ax.set_title("Emergency vs Normal Appointments", fontsize=14)
        ax.set_ylabel("Count")
        ax.legend(["Normal", "Emergency"])
        plt.xticks(rotation=45, ha="right")
        plt.tight_layout()
        path = os.path.join(output_dir, "chart_emergency_vs_normal.png")
        fig.savefig(path, dpi=100)
        plt.close(fig)
        charts.append(path)
    except Exception as e:
        print(f"Chart error: {e}")

    return charts


# ─── Main report generator ──────────────────────────────────────────────────

async def generate_full_report(output_dir: str = ".") -> dict:
    """Generate a complete analytics report with data and charts."""
    data = await fetch_appointment_data(days_back=90)
    ratings = await fetch_doctor_ratings()

    report = {
        "generated_at": datetime.now().isoformat(),
        "period": "Last 90 days",
        "busiest_doctors": analyze_busiest_doctors(data),
        "peak_hours": analyze_peak_hours(data),
        "status_distribution": analyze_status_distribution(data),
        "doctor_ratings": analyze_doctor_ratings(ratings),
    }

    # Generate charts
    charts = generate_charts(data, output_dir)
    report["charts"] = charts

    return report


# ─── CLI entry point ────────────────────────────────────────────────────────

if __name__ == "__main__":
    import json

    async def main():
        report = await generate_full_report(output_dir=".")
        print(json.dumps(report, indent=2, default=str))
        if report.get("charts"):
            print(f"\nCharts saved: {', '.join(report['charts'])}")

    asyncio.run(main())
