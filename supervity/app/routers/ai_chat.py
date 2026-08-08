# app/routers/ai_chat.py
"""
AI Manager (Orchestrator) chat endpoint.

The frontend AIManager component posts to /api/ai/chat with a message,
chat history, and page context. The orchestrator:
1. Inspects the message for data intents (stats, exceptions, policies, forecast)
2. Runs the matching "tools" against the database and records them as tool_calls
3. Sends the message + tool results to the LLM (NVIDIA NIM primary — the
   "brain" — with Gemini as secondary) and returns the response
"""

import logging
import uuid
from typing import Any, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..services.llm_service import llm
from ..services.audit import audit, AuditCategory, AuditSeverity

log = logging.getLogger(__name__)

router = APIRouter(prefix="/ai", tags=["AI Manager"])


class ChatHistoryItem(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    message: str
    history: list[ChatHistoryItem] = []
    context: Optional[dict] = None


# ---------------------------------------------------------------------------
# Orchestrator tools — deterministic data lookups the AI can ground itself on
# ---------------------------------------------------------------------------

def _tool_dashboard_stats(db: Session) -> dict:
    return {
        "total_leads": db.execute(text("SELECT COUNT(*) FROM contact")).scalar() or 0,
        "active_opportunities": db.execute(
            text('SELECT COUNT(*) FROM opportunity WHERE "IsClosed" = false OR "IsClosed" IS NULL')
        ).scalar() or 0,
        "pipeline_value": float(db.execute(
            text('SELECT COALESCE(SUM(CAST("Amount" AS NUMERIC)), 0) FROM opportunity WHERE "IsClosed" = false OR "IsClosed" IS NULL')
        ).scalar() or 0),
        "pending_exceptions": db.execute(
            text("SELECT COUNT(*) FROM exceptions WHERE status = 'pending'")
        ).scalar() or 0,
        "active_policies": db.execute(
            text("SELECT COUNT(*) FROM policies WHERE is_active = true")
        ).scalar() or 0,
    }


def _tool_pending_exceptions(db: Session) -> list[dict]:
    rows = db.execute(text(
        "SELECT id, type, severity, title, ai_recommendation FROM exceptions WHERE status = 'pending' ORDER BY created_at DESC LIMIT 10"
    )).mappings().all()
    return [dict(r) for r in rows]


def _tool_active_policies(db: Session) -> list[dict]:
    rows = db.execute(text(
        "SELECT id, name, natural_language, priority FROM policies WHERE is_active = true ORDER BY priority LIMIT 10"
    )).mappings().all()
    return [dict(r) for r in rows]


def _tool_revenue_forecast(db: Session) -> dict:
    won = db.execute(text('SELECT COUNT(*) FROM opportunity WHERE "IsWon" = true')).scalar() or 0
    closed = db.execute(text('SELECT COUNT(*) FROM opportunity WHERE "IsClosed" = true')).scalar() or 0
    win_rate = (won / closed) if closed else 0.0
    pipeline = float(db.execute(
        text('SELECT COALESCE(SUM(CAST("Amount" AS NUMERIC)), 0) FROM opportunity WHERE "IsClosed" = false OR "IsClosed" IS NULL')
    ).scalar() or 0)
    return {
        "win_rate": round(win_rate, 3),
        "open_pipeline": pipeline,
        "predicted_revenue": round(pipeline * win_rate, 2),
    }


def _tool_deduplication_summary(db: Session) -> dict:
    dup_groups = db.execute(text(
        'SELECT duplicate_key, COUNT(*) AS cnt FROM contact '
        'WHERE duplicate_key IS NOT NULL AND duplicate_key != \'\' '
        'GROUP BY duplicate_key HAVING COUNT(*) >= 2'
    )).mappings().all()
    return {
        "duplicate_group_count": len(dup_groups),
        "largest_group_size": max((g["cnt"] for g in dup_groups), default=0),
        "sample_keys": [g["duplicate_key"] for g in dup_groups[:5]],
    }


TOOL_TRIGGERS: list[tuple[str, tuple[str, ...], Any]] = [
    ("get_dashboard_stats", ("stat", "kpi", "dashboard", "lead", "overview", "summary"), _tool_dashboard_stats),
    ("get_pending_exceptions", ("exception", "error", "workbench", "review", "pending"), _tool_pending_exceptions),
    ("get_active_policies", ("policy", "policies", "rule", "automation"), _tool_active_policies),
    ("get_revenue_forecast", ("forecast", "revenue", "predict", "pipeline", "win rate"), _tool_revenue_forecast),
    ("get_deduplication_summary", ("duplicate", "dedup", "merge", "contact", "deduplication"), _tool_deduplication_summary),
]


@router.post("/chat")
def ai_chat(req: ChatRequest, db: Session = Depends(get_db)):
    """Orchestrated AI chat: run data tools based on intent, then ask the LLM."""
    message_lower = req.message.lower()

    # 1. Run matching tools
    tool_calls = []
    tool_context: dict[str, Any] = {}
    for name, triggers, fn in TOOL_TRIGGERS:
        if any(t in message_lower for t in triggers):
            try:
                result = fn(db)
                tool_calls.append({"id": str(uuid.uuid4()), "name": name, "args": {}, "result": result})
                tool_context[name] = result
            except Exception as e:
                log.warning(f"AI chat tool {name} failed: {e}")

    # 2. Build the prompt
    history_text = "\n".join(f"{h.role}: {h.content}" for h in req.history[-10:])
    page = (req.context or {}).get("page", "/")

    tool_summary = "\n".join(
        f"Tool '{name}': {fn.__doc__.strip() if fn.__doc__ else 'Run data lookup.'}"
        for name, _, fn in TOOL_TRIGGERS
    )

    prompt_parts = [
        "You are AutoPilot AI, the orchestrator assistant of a sales command center.",
        f"The user is currently on page: {page}",
        "You have access to the following deterministic tools. Use them when the user's question matches their purpose:",
        tool_summary,
    ]
    if history_text:
        prompt_parts.append(f"Conversation so far:\n{history_text}")
    if tool_context:
        import json as _json
        prompt_parts.append(f"Live data pulled from the system (use these real numbers):\n{_json.dumps(tool_context, default=str)}")
    prompt_parts.append(
        f"User message: {req.message}\n\n"
        "Answer concisely and helpfully in plain text (no markdown headers). "
        "If live data is provided, ground every number and conclusion in it. "
        "When the user wants to take action (merge, approve, reject, create a policy), explain what you would do, "
        "which page to visit, and any safety checks they should consider. "
        "If you cannot do the action yourself, point them to the right page (Workbench, Data Manager, AI Policies, AI Insights). "
        "If the user asks a vague question, ask one clarifying question before using data."
    )
    prompt = "\n\n".join(prompt_parts)

    # 3. Ask the LLM — NIM (the "brain") first, Gemini as backup
    llm_notice = None
    model_used = None
    try:
        response = llm.nemotron(
            prompt,
            system_prompt=(
                "You are AutoPilot AI, the orchestrator of a sales command center. "
                "You are grounded, concise, and safe. Always base your answers on the live data provided. "
                "Never invent numbers. If data is missing, say so and ask the user for the missing input. "
                "When the user wants to take an action, explain the steps and direct them to the correct app page. "
                "Respond in plain text only, no markdown."
            ),
        )
        if isinstance(response, (dict, list)):
            import json as _json
            response = _json.dumps(response, default=str)
        model_used = "nemotron"
    except Exception as nim_err:
        log.warning(f"Nemotron chat failed ({nim_err}); trying Gemini")
        try:
            response = llm.gemini(prompt)
            model_used = "gemini"
            llm_notice = "NVIDIA NIM is unavailable — this response was generated by Google Gemini as a fallback."
        except Exception as gem_err:
            log.error(f"Both LLMs failed for chat: {gem_err}")
            # Still useful: answer from tool data alone
            if tool_context:
                import json as _json
                response = (
                    "Both AI models are currently unavailable, but here is the live data I found: "
                    + _json.dumps(tool_context, default=str)
                )
                llm_notice = "Gemini quota is out and NVIDIA NIM is unavailable — showing raw data only."
            else:
                response = "Both AI models are currently unavailable. Please check the LLM API keys/quota and try again."
                llm_notice = "Gemini quota is out and NVIDIA NIM is unavailable."

    return {
        "response": response,
        "tool_calls": tool_calls,
        "model_used": model_used,
        "llm_notice": llm_notice,
    }


class DraftReminderRequest(BaseModel):
    owner_name: str
    owner_email: str
    insight_title: str
    insight_description: str
    suggested_action: str
    consequence: str


@router.post("/draft-reminder")
def draft_reminder(req: DraftReminderRequest):
    """Draft a follow-up reminder email to an insight owner."""
    prompt = f"""You are the sales operations assistant for a revenue command center.

Write a concise, urgent follow-up email to {req.owner_name} ({req.owner_email}) about this insight:

Title: {req.insight_title}
Description: {req.insight_description}
Suggested action: {req.suggested_action}
Risk if no follow-up is made: {req.consequence}

Return ONLY a JSON object with two keys:
- subject: a clear, action-oriented email subject
- body: a short, professional email body in plain text with newlines
"""
    try:
        result = llm.gemini_json(prompt=prompt, data={})
        audit.log_sync(
            action="ai.draft_reminder",
            description=f"Drafted reminder email to {req.owner_name}.",
            category=AuditCategory.DATA,
            severity=AuditSeverity.INFO,
            resource_type="insight",
            resource_name=req.insight_title,
            metadata={"owner_email": req.owner_email},
            actor={"id": "ai-insights", "email": "ai-insights@supervity.ai"},
        )
        return {"subject": result.get("subject", "Follow-up required"), "body": result.get("body", "")}
    except Exception as e:
        log.error(f"Draft reminder error: {e}")
        raise HTTPException(status_code=500, detail="Failed to draft reminder email")
