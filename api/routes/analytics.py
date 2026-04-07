"""
Analytics API routes — exposes data science reports via REST API.
"""
from fastapi import APIRouter, Depends, Query
from config.auth import get_current_user
from analytics.reports import (
    fetch_appointment_data, fetch_doctor_ratings,
    analyze_busiest_doctors, analyze_peak_hours,
    analyze_status_distribution, analyze_doctor_ratings,
    generate_full_report
)

router = APIRouter(prefix="/api/analytics", tags=["analytics"])


@router.get("/report")
async def get_full_report(
    days: int = Query(90, description="Number of days to analyze"),
    user: dict = Depends(get_current_user)
):
    """Generate a full analytics report (busiest doctors, peak hours, status distribution, ratings)."""
    data = await fetch_appointment_data(days_back=days)
    ratings = await fetch_doctor_ratings()

    return {
        "busiest_doctors": analyze_busiest_doctors(data),
        "peak_hours": analyze_peak_hours(data),
        "status_distribution": analyze_status_distribution(data),
        "doctor_ratings": analyze_doctor_ratings(ratings),
    }


@router.get("/busiest-doctors")
async def get_busiest_doctors(
    days: int = Query(30, description="Number of days to analyze"),
    user: dict = Depends(get_current_user)
):
    """Get busiest doctor rankings."""
    data = await fetch_appointment_data(days_back=days)
    return analyze_busiest_doctors(data)


@router.get("/peak-hours")
async def get_peak_hours(
    days: int = Query(30, description="Number of days to analyze"),
    user: dict = Depends(get_current_user)
):
    """Get peak booking hours analysis."""
    data = await fetch_appointment_data(days_back=days)
    return analyze_peak_hours(data)
