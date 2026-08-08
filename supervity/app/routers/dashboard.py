# app/routers/dashboard.py
"""Dashboard endpoints — live KPIs computed from the database."""

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import func, text
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..services.llm_service import llm

log = logging.getLogger(__name__)

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


from typing import Optional, Any

@router.get("/stats")
def get_dashboard_stats(viewer_role: Optional[str] = None, viewer_id: Optional[str] = None, db: Session = Depends(get_db)):
    """
    Returns live KPI statistics computed from the seeded database tables.
    This replaces the hardcoded stats on the frontend dashboard.
    """
    try:
        contact_where = ""
        opp_where = ""
        params: dict[str, Any] = {}
        
        if viewer_role == "sdr" and viewer_id:
            contact_where = "WHERE c.\"OwnerId\" = :viewer_id AND c.\"Lead_Stage__c\" = 'Open'"
            opp_where = "AND o.\"OwnerId\" = :viewer_id"
            params["viewer_id"] = viewer_id
        elif viewer_role == "sales_agent" and viewer_id:
            contact_where = "WHERE c.\"Lead_Stage__c\" IN ('Opportunity','MQL') AND c.\"OwnerId\" IN (SELECT owner_id FROM sdr_roster WHERE sales_agent_id = :viewer_id)"
            opp_where = "AND o.\"OwnerId\" IN (SELECT owner_id FROM sdr_roster WHERE sales_agent_id = :viewer_id)"
            params["viewer_id"] = viewer_id
        elif viewer_role == "manager" and viewer_id:
            contact_where = "WHERE c.\"Lead_Stage__c\" = 'SQL' AND c.\"OwnerId\" IN (SELECT owner_id FROM sdr_roster sr JOIN sales_agents sa ON sr.sales_agent_id = sa.id WHERE sa.sales_manager_id = :viewer_id)"
            opp_where = "AND o.\"OwnerId\" IN (SELECT owner_id FROM sdr_roster sr JOIN sales_agents sa ON sr.sales_agent_id = sa.id WHERE sa.sales_manager_id = :viewer_id)"
            params["viewer_id"] = viewer_id

        # Total Leads (contacts)
        total_leads = db.execute(text(f"SELECT COUNT(*) FROM contact c {contact_where}"), params).scalar() or 0

        # Active Opportunities
        active_opps = db.execute(
            text(f"SELECT COUNT(*) FROM opportunity o WHERE (o.\"IsClosed\" = false OR o.\"IsClosed\" IS NULL) {opp_where}"), params
        ).scalar() or 0

        # Pipeline Value
        pipeline_value = db.execute(
            text(f"SELECT COALESCE(SUM(CAST(o.\"Amount\" AS NUMERIC)), 0) FROM opportunity o WHERE (o.\"IsClosed\" = false OR o.\"IsClosed\" IS NULL) {opp_where}"), params
        ).scalar() or 0

        # Win Rate
        total_closed = db.execute(text(f"SELECT COUNT(*) FROM opportunity o WHERE o.\"IsClosed\" = true {opp_where}"), params).scalar() or 0
        total_won = db.execute(text(f"SELECT COUNT(*) FROM opportunity o WHERE o.\"IsWon\" = true {opp_where}"), params).scalar() or 0
        win_rate = round((total_won / total_closed * 100), 1) if total_closed > 0 else 0

        # Active SDRs
        active_sdrs = db.execute(text("SELECT COUNT(*) FROM sdr_roster WHERE active = true")).scalar() or 0

        # Visitor Activity count
        # Could scope to prospect_id IN (contacts), but keeping global for now as stats
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
        }

@router.get("/forecast")
def get_revenue_forecast(db: Session = Depends(get_db)):
    """
    Analyzes Opportunity and VisitorActivity tables to calculate win rate and predict revenue.
    Returns an AI generated short paragraph forecast.
    """
    try:
        # Calculate current metrics
        total_closed = db.execute(text("SELECT COUNT(*) FROM opportunity WHERE \"IsClosed\" = true")).scalar() or 0
        total_won = db.execute(text("SELECT COUNT(*) FROM opportunity WHERE \"IsWon\" = true")).scalar() or 0
        win_rate = round((total_won / total_closed * 100), 1) if total_closed > 0 else 0
        
        open_pipeline = db.execute(
            text("SELECT COALESCE(SUM(CAST(\"Amount\" AS NUMERIC)), 0) FROM opportunity WHERE \"IsClosed\" = false OR \"IsClosed\" IS NULL")
        ).scalar() or 0
        
        activities_last_30 = db.execute(
            text("SELECT COUNT(*) FROM visitoractivity")
        ).scalar() or 0

        prompt = f"""
        You are an expert Chief Revenue Officer (CRO) AI assistant. 
        Analyze the following sales pipeline data and provide a concise, 2-3 sentence revenue forecast for the next 30 days. 
        Focus on the projected revenue (applying the win rate to the pipeline) and what the visitor activity implies about future pipeline.
        
        Data:
        - Current Win Rate: {win_rate}%
        - Open Pipeline Value: ${float(open_pipeline):,.2f}
        - Total Deals Closed Won: {total_won}
        - Recent Visitor Activities: {activities_last_30}
        
        Return ONLY the raw text response, no markdown, no introductions. Make it sound professional, data-driven, and insightful.
        """
        
        result = llm.gemini(prompt)
        return {"forecast": result.strip()}
    except Exception as e:
        log.error(f"Failed to generate forecast: {e}")
        return {"forecast": "Unable to generate forecast at this time due to missing data or an error."}
