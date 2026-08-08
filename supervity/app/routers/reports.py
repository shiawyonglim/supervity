# app/routers/reports.py
"""Weekly revenue / performance report with role leaderboards and forecasting."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.database import get_db

log = logging.getLogger(__name__)
router = APIRouter(prefix="/reports", tags=["Reports"])


class WeeklyReport(BaseModel):
    week_of: str
    total_revenue: float
    pipeline_value: float
    total_opportunities: int
    won_opportunities: int
    lost_opportunities: int
    open_opportunities: int
    expected_closes_next_week: int
    expected_revenue_next_week: float
    leaderboard: list
    by_role: dict
    what_to_expect_next_week: str


@router.get("/weekly", response_model=WeeklyReport)
def weekly_report(
    weeks_ahead: int = Query(1, ge=0, le=4, description="Number of weeks to forecast"),
    db: Session = Depends(get_db),
):
    """
    Generate a weekly performance report:
      - total revenue (won opportunities)
      - current pipeline value
      - expected closes/revenue for the next N weeks
      - leaderboards by owner and by role (SDR / Sales Agent / Manager / CRO)
    """
    try:
        today = datetime.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        horizon_end = week_start + timedelta(weeks=weeks_ahead, days=6)

        # Core aggregates
        agg = db.execute(text("""
            SELECT
                COALESCE(SUM(CASE WHEN "IsWon" = TRUE THEN "Amount" ELSE 0 END), 0) AS total_revenue,
                COALESCE(SUM(CASE WHEN "IsClosed" = FALSE THEN "Amount" ELSE 0 END), 0) AS pipeline_value,
                COUNT(*) AS total_opportunities,
                SUM(CASE WHEN "IsWon" = TRUE THEN 1 ELSE 0 END) AS won,
                SUM(CASE WHEN "IsClosed" = TRUE AND "IsWon" = FALSE THEN 1 ELSE 0 END) AS lost,
                SUM(CASE WHEN "IsClosed" = FALSE THEN 1 ELSE 0 END) AS open
            FROM opportunity
        """)).mappings().first()

        # Expected closes in the next N weeks (open opps with CloseDate inside horizon)
        forecast = db.execute(text("""
            SELECT
                COUNT(*) AS expected_closes,
                COALESCE(SUM("Amount" * ("Probability"::float / 100.0)), 0) AS expected_revenue
            FROM opportunity
            WHERE "IsClosed" = FALSE
              AND "CloseDate" IS NOT NULL
              AND to_date("CloseDate", 'MM/DD/YYYY') BETWEEN :start AND :end
        """), {"start": week_start.isoformat(), "end": horizon_end.isoformat()}).mappings().first()

        # Leaderboard by owner, joined to org tables for names/roles
        leaderboard_rows = db.execute(text("""
            WITH owners AS (
                SELECT owner_id AS id, name, 'SDR' AS role, territory FROM sdr_roster WHERE active = TRUE
                UNION ALL
                SELECT agent_id, name, 'Sales Agent', region FROM sales_agent
                UNION ALL
                SELECT manager_id, name, 'Manager', region FROM manager
                UNION ALL
                SELECT cro_id, name, 'CRO', NULL FROM cro
            )
            SELECT
                COALESCE(o."OwnerId", 'unknown') AS owner_id,
                COALESCE(owners.name, o."OwnerId") AS name,
                COALESCE(owners.role, 'Unknown') AS role,
                COUNT(*) AS opportunities,
                COALESCE(SUM(o."Amount"), 0) AS revenue,
                SUM(CASE WHEN o."IsWon" = TRUE THEN 1 ELSE 0 END) AS won,
                SUM(CASE WHEN o."IsClosed" = TRUE AND o."IsWon" = FALSE THEN 1 ELSE 0 END) AS lost,
                SUM(CASE WHEN o."IsClosed" = FALSE
                         AND o."CloseDate" IS NOT NULL
                         AND to_date(o."CloseDate", 'MM/DD/YYYY') BETWEEN :start AND :end
                    THEN 1 ELSE 0 END) AS expected_closes,
                COALESCE(SUM(CASE WHEN o."IsClosed" = FALSE
                                  AND o."CloseDate" IS NOT NULL
                                  AND to_date(o."CloseDate", 'MM/DD/YYYY') BETWEEN :start AND :end
                             THEN o."Amount" * (o."Probability"::float / 100.0)
                             ELSE 0 END), 0) AS expected_revenue
            FROM opportunity o
            LEFT JOIN owners ON o."OwnerId" = owners.id
            GROUP BY o."OwnerId", owners.name, owners.role
            ORDER BY revenue DESC
        """), {"start": week_start.isoformat(), "end": horizon_end.isoformat()}).mappings().all()

        leaderboard = [dict(r) for r in leaderboard_rows]

        # By-role rollups
        by_role: dict = {}
        for row in leaderboard:
            role = row.get("role") or "Unknown"
            if role not in by_role:
                by_role[role] = {"owners": [], "opportunities": 0, "revenue": 0.0, "won": 0, "lost": 0, "expected_closes": 0, "expected_revenue": 0.0}
            for k in ("opportunities", "won", "lost", "expected_closes"):
                by_role[role][k] += int(row.get(k, 0) or 0)
            for k in ("revenue", "expected_revenue"):
                by_role[role][k] += float(row.get(k, 0.0) or 0.0)
            by_role[role]["owners"].append({
                "owner_id": row.get("owner_id"),
                "name": row.get("name"),
                "opportunities": row.get("opportunities"),
                "revenue": row.get("revenue"),
                "expected_closes": row.get("expected_closes"),
            })

        # What to expect next week — plain text summary
        expected_closes = int(forecast.get("expected_closes") or 0)
        expected_revenue = float(forecast.get("expected_revenue") or 0.0)
        open_opps = int(agg.get("open") or 0)

        if expected_closes == 0:
            what_to_expect = f"No opportunities are forecast to close in the next {weeks_ahead} week(s). Focus on moving {open_opps} open opportunities forward."
        else:
            what_to_expect = (
                f"We expect {expected_closes} opportunity deal(s) to close in the next {weeks_ahead} week(s), "
                f"representing ~${expected_revenue:,.0f} in weighted revenue. "
                f"With {open_opps} open opportunities in the pipeline, the team should prioritize high-probability deals and clear blockers."
            )

        return WeeklyReport(
            week_of=week_start.isoformat(),
            total_revenue=float(agg.get("total_revenue") or 0),
            pipeline_value=float(agg.get("pipeline_value") or 0),
            total_opportunities=int(agg.get("total_opportunities") or 0),
            won_opportunities=int(agg.get("won") or 0),
            lost_opportunities=int(agg.get("lost") or 0),
            open_opportunities=int(agg.get("open") or 0),
            expected_closes_next_week=expected_closes,
            expected_revenue_next_week=expected_revenue,
            leaderboard=leaderboard,
            by_role=by_role,
            what_to_expect_next_week=what_to_expect,
        )

    except Exception as e:
        log.error(f"Weekly report error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
