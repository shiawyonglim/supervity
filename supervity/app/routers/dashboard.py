# app/routers/dashboard.py
"""Dashboard endpoints — live KPIs computed from the database."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from ..core.database import get_db

log = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats")
def get_dashboard_stats(db: Session = Depends(get_db)):
    """
    Returns live KPI statistics computed from the seeded database tables.
    This replaces the hardcoded stats on the frontend dashboard.
    """
    try:
        # Total Leads (contacts)
        total_leads = db.execute(text("SELECT COUNT(*) FROM contact")).scalar() or 0

        # Active Opportunities
        active_opps = db.execute(
            text("SELECT COUNT(*) FROM opportunity WHERE \"IsClosed\" = false OR \"IsClosed\" IS NULL")
        ).scalar() or 0

        # Pipeline Value
        pipeline_value = db.execute(
            text("SELECT COALESCE(SUM(CAST(\"Amount\" AS NUMERIC)), 0) FROM opportunity WHERE \"IsClosed\" = false OR \"IsClosed\" IS NULL")
        ).scalar() or 0

        # Win Rate
        total_closed = db.execute(text("SELECT COUNT(*) FROM opportunity WHERE \"IsClosed\" = true")).scalar() or 0
        total_won = db.execute(text("SELECT COUNT(*) FROM opportunity WHERE \"IsWon\" = true")).scalar() or 0
        win_rate = round((total_won / total_closed * 100), 1) if total_closed > 0 else 0

        # Active SDRs
        active_sdrs = db.execute(text("SELECT COUNT(*) FROM sdr_roster WHERE active = true")).scalar() or 0

        # Visitor Activity count
        total_activities = db.execute(text("SELECT COUNT(*) FROM visitoractivity")).scalar() or 0

        # Pending exceptions
        pending_exceptions = db.execute(
            text("SELECT COUNT(*) FROM exceptions WHERE status = 'pending'")
        ).scalar() or 0

        # Active policies
        active_policies = db.execute(
            text("SELECT COUNT(*) FROM policies WHERE is_active = true")
        ).scalar() or 0

        return {
            "total_leads": total_leads,
            "active_opportunities": active_opps,
            "pipeline_value": float(pipeline_value),
            "win_rate": win_rate,
            "active_sdrs": active_sdrs,
            "total_activities": total_activities,
            "pending_exceptions": pending_exceptions,
            "active_policies": active_policies,
        }

    except Exception as e:
        log.warning(f"Dashboard stats error (tables may not exist yet): {e}")
        # Return zeros if tables don't exist yet
        return {
            "total_leads": 0,
            "active_opportunities": 0,
            "pipeline_value": 0.0,
            "win_rate": 0.0,
            "active_sdrs": 0,
            "total_activities": 0,
            "pending_exceptions": 0,
            "active_policies": 0,
        }
