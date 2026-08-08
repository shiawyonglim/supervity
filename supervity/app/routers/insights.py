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
    Falls back to NVIDIA NIM (Nemotron) when Gemini is unavailable (e.g. quota).
    Returns a step-by-step `trace` of how the AI worked (deep auditability).
    """
    trace: list[dict] = []

    def _step(step: str, detail: str):
        trace.append({"step": len(trace) + 1, "action": step, "detail": detail})

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

        exceptions = db.execute(text(
            "SELECT id, type as error_type, context as payload, resolution_action FROM exceptions WHERE status = 'resolved' ORDER BY resolved_at DESC LIMIT 20"
        )).mappings().all()

        # The real people an insight can be assigned to. Passing this in means the
        # model names an actual rep from the roster instead of inventing someone.
        sdrs = db.execute(text(
            "SELECT owner_id, name, email, territory, region, segment, "
            "current_capacity, max_capacity, active FROM sdr_roster"
        )).mappings().all()

        # Convert to dicts for JSON serialization
        contacts_data = [dict(r) for r in contacts]
        activities_data = [dict(r) for r in activities]
        opportunities_data = [dict(r) for r in opportunities]
        exceptions_data = [dict(r) for r in exceptions]
        sdr_data = [dict(r) for r in sdrs]

        combined_data = {
            "contacts": contacts_data,
            "visitor_activities": activities_data,
            "opportunities": opportunities_data,
            "recent_resolved_exceptions": exceptions_data,
            "sdr_roster": sdr_data,
        }

        _step(
            "fetch_data",
            f"Pulled {len(contacts_data)} contacts, {len(activities_data)} visitor activities, "
            f"{len(opportunities_data)} opportunities, {len(exceptions_data)} resolved exceptions, "
            f"and {len(sdr_data)} SDR roster entries from the database.",
        )

        prompt = """Analyze this sales intelligence data and generate exactly 3-5 insights.

EVERY insight must answer three questions explicitly. An insight that does not name a
person, a concrete next step, and a real consequence is useless — do not produce one.

1. WHO IS THIS FOR?
   - owner_name: the specific person who must act. Use a REAL name from the `sdr_roster`
     data whenever the insight concerns their leads, territory, capacity, or deals.
     Only if the insight is genuinely operation-wide (e.g. a policy or data-quality
     issue that no single rep owns) may you use a role title such as
     "Revenue Ops Manager" or "Sales Manager". NEVER invent a person's name.
   - owner_role: their role and patch, e.g. "SDR — MY Enterprise". Derive from the
     roster's territory/region/segment fields.
   - owner_id: the matching `owner_id` from `sdr_roster` (starts with 005). Use null
     when the owner is a role rather than a specific rostered person.

2. WHAT SHOULD THEY DO NOW?
   - suggested_action: one concrete, immediately executable instruction addressed to
     that person. Name the specific records, accounts, or thresholds involved and how
     many. Good: "Re-assign the 4 overflow leads on the Penang Semiconductor account to
     Grace Lim before Friday." Bad: "Review lead routing."

3. WHAT HAPPENS IF THEY DON'T?
   - consequence: the concrete business cost of inaction, quantified from the data
     where possible — revenue at risk, deals that will stall, compliance exposure,
     leads that will go cold, SLA breaches. Good: "The 4 leads breach the 24-hour
     speed-to-lead SLA and ~$180K of pipeline goes cold; Wei Ho stays 2 over capacity
     so the next inbound lead is also dropped." Bad: "Performance may suffer."

Also provide:
- type: "pattern", "anomaly", or "recommendation"
- severity: "critical", "warning", or "info"
- title: a short descriptive title
- description: 1-2 sentence explanation of what you observed in the data
- confidence: a float between 0.0 and 1.0
- action_type: "create_policy", "investigate", "review_duplicate", or "optimize"
- data: if action_type is "create_policy", include a JSON dict with "policy_type" ("natural_language"), "natural_language" (the rule), and "entity_name"

Return a JSON array of insight objects. YOU MUST FOCUS ON:
1. Pattern recognition for buying probability: Correlate VisitorActivities and Contact data with Opportunities where IsWon=True to identify which patterns (e.g., campaigns, specific web pages, regions) have a higher probability of buying stuff.
2. Automation from Exceptions: Analyze the `recent_resolved_exceptions`. If human operators have manually performed the same `resolution_action` (e.g., mapping fields, merging records like 'IBM' and 'Intl Business Machines') multiple times, generate a Recommendation with action_type="create_policy" asking the user: "Human operators manually performed X recently. Would you like me to create an AI Policy to automate this in the future?". Provide the policy details in the `data` field.
3. Rep-level operational risk: over-capacity SDRs, stalled deals, and unworked high-intent leads — these map naturally onto a named owner from the roster.

Be specific about the numbers you see in the data."""

        _step("build_prompt", "Constructed analysis prompt requiring each insight to name an owner (from the SDR roster), a concrete next action, and the consequence of inaction.")

        result, llm_meta = llm.smart_json(prompt=prompt, data=combined_data)
        _step(
            "llm_analysis",
            f"Analyzed data with {llm_meta['model_used']}."
            + (f" NOTE: {llm_meta['llm_notice']}" if llm_meta.get("llm_notice") else ""),
        )

        # Save insights to database
        saved_insights = []
        insights_list = result if isinstance(result, list) else [result]
        _step("parse_response", f"Parsed {len(insights_list)} insight(s) from the model's JSON response.")
        for item in insights_list:
            insight_data = item.get("data") or {}
            if not isinstance(insight_data, dict):
                insight_data = {"payload": insight_data}
            insight_data["ai_trace"] = trace
            insight_data["model_used"] = llm_meta.get("model_used")
            insight_data["llm_notice"] = llm_meta.get("llm_notice")

            db_insight = InsightModel(
                type=item.get("type", "pattern"),
                severity=item.get("severity", "info"),
                title=item.get("title", "Generated Insight"),
                description=item.get("description", ""),
                data=insight_data,
                owner_name=item.get("owner_name"),
                owner_role=item.get("owner_role"),
                owner_id=item.get("owner_id"),
                suggested_action=item.get("suggested_action"),
                consequence=item.get("consequence"),
                action_type=item.get("action_type"),
                confidence=item.get("confidence", 0.5) or 0.0,
            )
            db.add(db_insight)
            saved_insights.append(db_insight)

        db.commit()
        for ins in saved_insights:
            db.refresh(ins)

        _step("persist", f"Saved {len(saved_insights)} insight(s) to the database.")

        return {
            "status": "success",
            "count": len(saved_insights),
            "insights": saved_insights,
            "trace": trace,
            "model_used": llm_meta.get("model_used"),
            "llm_notice": llm_meta.get("llm_notice"),
        }

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        log.error(f"Insight generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/self-learn")
def self_learn(db: Session = Depends(get_db)):
    """
    Self-learning (no LLM needed): scan resolved exceptions for repeated
    manual resolutions. If human operators performed the same action for the
    same exception type 2+ times, suggest an AI Policy to automate it.
    """
    rows = db.execute(text(
        "SELECT type, resolution_action, COUNT(*) AS cnt, MAX(title) AS sample_title "
        "FROM exceptions WHERE status = 'resolved' AND resolution_action = 'approved' "
        "GROUP BY type, resolution_action HAVING COUNT(*) >= 2 ORDER BY cnt DESC"
    )).mappings().all()

    created = []
    for row in rows:
        exc_type = row["type"]
        count = row["cnt"]
        title = f"Automate '{exc_type}' resolutions"

        # Skip if we already suggested this
        existing = db.query(InsightModel).filter(
            InsightModel.title == title,
            InsightModel.action_type == "create_policy",
        ).first()
        if existing:
            continue

        rule = (
            f"When an exception of type '{exc_type}' occurs and the AI confidence is above 80%, "
            f"automatically approve it the same way human operators have done, and log the decision in the audit trail."
        )
        insight = InsightModel(
            type="recommendation",
            severity="info",
            title=title,
            description=(
                f"Human operators manually approved '{exc_type}' exceptions {count} times "
                f"(e.g. \"{row['sample_title']}\"). Would you like me to create an AI Policy to automate this in the future?"
            ),
            data={
                "policy_type": "natural_language",
                "natural_language": rule,
                "entity_name": "exception",
                "learned_from": {"exception_type": exc_type, "occurrences": count},
            },
            # This is an operation-wide governance decision, not one rep's job.
            owner_name="Revenue Ops Manager",
            owner_role="Owner of the AI Policies engine",
            owner_id=None,
            suggested_action=(
                f"Open AI Policies and create the suggested rule so '{exc_type}' exceptions "
                f"with confidence above 80% are auto-approved instead of queued for a human."
            ),
            consequence=(
                f"Operators keep clearing '{exc_type}' exceptions by hand — at the current rate "
                f"that is {count} repeat resolutions already, and every future one costs review "
                f"time and delays the affected leads while they sit in the Workbench queue."
            ),
            action_type="create_policy",
            confidence=min(0.5 + 0.1 * count, 0.95),
        )
        db.add(insight)
        created.append(insight)

    db.commit()
    for ins in created:
        db.refresh(ins)

    return {
        "status": "success",
        "patterns_found": len(rows),
        "insights_created": len(created),
        "insights": created,
    }

@router.get("/forecast")
def revenue_forecast(db: Session = Depends(get_db)):
    """Calculate current win rate and predict future revenue from open pipeline."""
    try:
        # Calculate Win Rate
        won_deals = db.execute(text('SELECT COUNT(*) FROM opportunity WHERE "IsWon" = true')).scalar() or 0
        lost_deals = db.execute(text('SELECT COUNT(*) FROM opportunity WHERE "IsClosed" = true AND "IsWon" = false')).scalar() or 0
        total_closed = won_deals + lost_deals
        win_rate = (won_deals / total_closed) if total_closed > 0 else 0.0

        # Calculate Open Pipeline
        open_pipeline = db.execute(text(
            'SELECT SUM(CAST("Amount" AS FLOAT)) FROM opportunity '
            'WHERE "IsClosed" = false OR "IsClosed" IS NULL'
        )).scalar() or 0.0

        predicted_revenue = open_pipeline * win_rate

        return {
            "win_rate": win_rate,
            "open_pipeline": open_pipeline,
            "predicted_revenue": predicted_revenue,
            "won_deals": won_deals,
            "lost_deals": lost_deals,
            "total_closed": total_closed
        }
    except Exception as e:
        log.error(f"Forecasting error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{insight_id}/trace")
def get_insight_trace(insight_id: int, db: Session = Depends(get_db)):
    """Return the step-by-step AI reasoning trace for a specific insight."""
    insight = db.query(InsightModel).filter(InsightModel.id == insight_id).first()
    if not insight:
        raise HTTPException(status_code=404, detail="Insight not found")

    if isinstance(insight.data, dict) and "ai_trace" in insight.data:
        trace = insight.data["ai_trace"]
    else:
        trace = []

    return {
        "insight_id": insight_id,
        "title": insight.title,
        "model_used": insight.data.get("model_used") if isinstance(insight.data, dict) else None,
        "llm_notice": insight.data.get("llm_notice") if isinstance(insight.data, dict) else None,
        "trace": trace,
    }


@router.get("/audit-trail")
def get_audit_trail(db: Session = Depends(get_db)):
    """Return the most recent AI reasoning traces across all insights."""
    insights = (
        db.query(InsightModel)
        .order_by(InsightModel.created_at.desc())
        .limit(50)
        .all()
    )

    trail = []
    for ins in insights:
        if isinstance(ins.data, dict) and "ai_trace" in ins.data:
            trail.append(
                {
                    "insight_id": ins.id,
                    "title": ins.title,
                    "created_at": ins.created_at,
                    "model_used": ins.data.get("model_used"),
                    "llm_notice": ins.data.get("llm_notice"),
                    "trace": ins.data["ai_trace"],
                }
            )

    return {"count": len(trail), "trail": trail}

