# app/routers/cro.py
"""CRO-specific endpoints: weekly email, scoreboard helpers, and team oversight."""

import logging
from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..services.llm_service import llm
from ..services.audit import audit, AuditCategory, AuditSeverity

log = logging.getLogger(__name__)

router = APIRouter(prefix="/cro", tags=["CRO"])


class WeeklyEmailRequest(BaseModel):
    revenue: Optional[float] = 0
    top_sdr: Optional[dict] = None
    top_customer: Optional[dict] = None


class WeeklyEmailSendRequest(BaseModel):
    to: str = "cro@supervity.ai"
    subject: str
    body: str


@router.post("/weekly-email")
def draft_weekly_email(req: WeeklyEmailRequest, db: Session = Depends(get_db)):
    """Draft a weekly CRO summary email with revenue, top SDR, and top customer."""
    try:
        revenue = req.revenue or 0.0
        top_sdr = req.top_sdr or {}
        top_customer = req.top_customer or {}

        # Pull extra summary data directly from the DB
        total_leads = db.execute(text("SELECT COUNT(*) FROM contact")).scalar() or 0
        active_opps = db.execute(
            text('SELECT COUNT(*) FROM opportunity WHERE "IsClosed" = false OR "IsClosed" IS NULL')
        ).scalar() or 0
        pipeline = float(db.execute(
            text('SELECT COALESCE(SUM(CAST("Amount" AS NUMERIC)), 0) FROM opportunity WHERE "IsClosed" = false OR "IsClosed" IS NULL')
        ).scalar() or 0)

        prompt = f"""You are the revenue operations assistant. Draft a concise, professional weekly CRO email summary.

Data:
- Total closed-won revenue: ${revenue:,.2f}
- Open pipeline: ${pipeline:,.2f}
- Active opportunities: {active_opps}
- Total leads: {total_leads}
- Top SDR: {top_sdr.get('name', 'N/A')} with {top_sdr.get('closed', 0)} closed won and ${top_sdr.get('value', 0):,.2f} value
- Top paying customer: {top_customer.get('name', 'N/A')} with ${top_customer.get('value', 0):,.2f} revenue

Return ONLY a JSON object with two keys:
- subject: a clear weekly summary subject line
- body: a short, data-driven email body in plain text with newlines
"""

        result = llm.gemini_json(prompt=prompt, data={})
        return {
            "to": "cro@supervity.ai",
            "subject": result.get("subject", "Weekly Revenue Summary"),
            "body": result.get("body", "Weekly revenue summary unavailable."),
        }
    except Exception as e:
        log.error(f"Weekly email draft error: {e}")
        return {
            "to": "cro@supervity.ai",
            "subject": "Weekly Revenue Summary",
            "body": f"Weekly revenue: ${req.revenue:,.2f}\nTop SDR: {req.top_sdr.get('name', 'N/A')}\nTop paying customer: {req.top_customer.get('name', 'N/A')}",
        }


@router.post("/weekly-email/send")
def send_weekly_email(req: WeeklyEmailSendRequest):
    """Queue the weekly CRO email. SMTP is not configured in this environment; the email is logged."""
    audit.log_sync(
        action="cro.weekly_email",
        description=f"Queued weekly CRO email to {req.to} with subject '{req.subject}'",
        category=AuditCategory.DATA,
        severity=AuditSeverity.INFO,
        resource_type="email",
        resource_name=req.subject,
        metadata={"to": req.to, "subject": req.subject, "body_preview": req.body[:500]},
        actor={"id": "cro-dashboard", "email": "cro-dashboard@supervity.ai"},
    )
    return {"status": "queued", "to": req.to, "subject": req.subject}
