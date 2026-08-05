# app/routers/insights.py
"""AI Insights endpoints — AI-generated observations from the data."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import text

from ..core.database import get_db
from ..models.insight import Insight as InsightModel
from ..schemas.insight import Insight, InsightCreate
from ..services.llm_service import llm

log = logging.getLogger(__name__)

router = APIRouter(prefix="/insights", tags=["AI Insights"])


@router.get("", response_model=list[Insight])
def list_insights(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    """List all AI-generated insights."""
    return db.query(InsightModel).order_by(InsightModel.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=Insight)
def create_insight(insight: InsightCreate, db: Session = Depends(get_db)):
    """Manually create an insight."""
    db_insight = InsightModel(**insight.model_dump())
    db.add(db_insight)
    db.commit()
    db.refresh(db_insight)
    return db_insight


@router.post("/generate")
def generate_insights(db: Session = Depends(get_db)):
    """
    Use Gemini to analyze the database and generate AI insights.
    Pulls recent data from VisitorActivity, Contact, and Opportunity tables
    and asks the LLM to find patterns, anomalies, and recommendations.
    """
    try:
        # Fetch summary data for the LLM to analyze
        contacts = db.execute(text(
            "SELECT region, \"Lead_Stage__c\", \"LeadSource\", confidence FROM contact LIMIT 100"
        )).mappings().all()

        activities = db.execute(text(
            "SELECT type, url, source, channel, duration_seconds FROM visitoractivity LIMIT 100"
        )).mappings().all()

        opportunities = db.execute(text(
            "SELECT \"StageName\", \"Amount\", \"Probability\", \"LeadSource\", \"IsClosed\", \"IsWon\" FROM opportunity LIMIT 50"
        )).mappings().all()

        # Convert to dicts for JSON serialization
        contacts_data = [dict(r) for r in contacts]
        activities_data = [dict(r) for r in activities]
        opportunities_data = [dict(r) for r in opportunities]

        combined_data = {
            "contacts": contacts_data,
            "visitor_activities": activities_data,
            "opportunities": opportunities_data,
        }

        prompt = """Analyze this sales intelligence data and generate exactly 3-5 insights.
For each insight, provide:
- type: "pattern", "anomaly", or "recommendation"
- severity: "critical", "warning", or "info"
- title: a short descriptive title
- description: 1-2 sentence explanation
- confidence: a float between 0.0 and 1.0
- suggested_action: what should be done about this
- action_type: "create_policy", "investigate", "review_duplicate", or "optimize"

Return a JSON array of insight objects. Focus on:
1. Lead source performance patterns
2. Regional activity anomalies
3. Pipeline health recommendations
4. Visitor behavior patterns
5. Conversion rate insights

Be specific about the numbers you see in the data."""

        result = llm.gemini_json(prompt=prompt, data=combined_data)

        # Save insights to database
        saved_insights = []
        insights_list = result if isinstance(result, list) else [result]
        for item in insights_list:
            db_insight = InsightModel(
                type=item.get("type", "pattern"),
                severity=item.get("severity", "info"),
                title=item.get("title", "Generated Insight"),
                description=item.get("description", ""),
                data=item.get("data"),
                suggested_action=item.get("suggested_action"),
                action_type=item.get("action_type"),
                confidence=item.get("confidence", 0.5),
            )
            db.add(db_insight)
            saved_insights.append(db_insight)

        db.commit()
        for ins in saved_insights:
            db.refresh(ins)

        return {
            "status": "success",
            "count": len(saved_insights),
            "insights": saved_insights,
        }

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        log.error(f"Insight generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
