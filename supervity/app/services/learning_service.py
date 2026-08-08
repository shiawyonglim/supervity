# app/services/learning_service.py
"""
Generate user-facing ContactContext and AI-facing Learning records from a contact's
profile, visitor activity, and email history.
"""

import json
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..models.context import ContactContext
from ..models.learning import Learning
from ..services.llm_service import llm

log = logging.getLogger(__name__)


def _to_bool(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("true", "1", "yes", "t")


def _try_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _compute_intent(contact: dict, activities: List[dict]) -> int:
    try:
        base = float(contact.get("confidence") or 0) * 100
    except (ValueError, TypeError):
        base = 50.0
    score = base

    source = (contact.get("LeadSource") or "").lower()
    if "pricing" in source or "demo" in source or "contact" in source:
        score += 20
    elif "referral" in source or "trade" in source:
        score += 15
    elif "content" in source or "webinar" in source or "newsletter" in source:
        score += 8

    stage = (contact.get("Lead_Stage__c") or "").lower()
    if stage in ("sql", "opportunity", "customer"):
        score += 15

    for a in activities:
        url = (a.get("url") or "").lower()
        dur = a.get("duration_seconds") or 0
        if url in ("/pricing", "/demo", "/contact"):
            score += 15
        elif url in ("/case-studies",):
            score += 10
        elif url and url != "/":
            score += 5

        if a.get("type", "").lower() in ("download", "click"):
            score += 5
        if dur and dur > 60:
            score += 5
        if dur and dur > 300:
            score += 5

    if len(activities) >= 3:
        score += 10

    return max(0, min(100, round(score)))


def _build_contact_summary(db: Session, contact_id: str) -> Dict[str, Any]:
    """Build a lightweight contact/activity/emails summary for context/learning generation."""
    contact = db.execute(text('SELECT * FROM contact WHERE "Id" = :id'), {"id": contact_id}).mappings().first()
    if not contact:
        return {}
    contact = dict(contact)

    account = None
    if contact.get("AccountId"):
        account = db.execute(text('SELECT * FROM account WHERE "Id" = :id'), {"id": contact["AccountId"]}).mappings().first()
        if account:
            account = dict(account)

    activities = db.execute(
        text('SELECT * FROM visitoractivity WHERE prospect_id = :id ORDER BY created_at DESC LIMIT 10'),
        {"id": contact_id},
    ).mappings().all()
    activities = [dict(a) for a in activities]

    from ..models.email import EmailLog
    emails = (
        db.query(EmailLog)
        .filter(EmailLog.contact_id == contact_id)
        .order_by(EmailLog.created_at.desc())
        .limit(20)
        .all()
    )

    intent_score = _compute_intent(contact, activities)

    privacy = "Can contact"
    if _to_bool(contact.get("HasOptedOutOfEmail")) and _to_bool(contact.get("DoNotCall")):
        privacy = "Do not email or call"
    elif _to_bool(contact.get("HasOptedOutOfEmail")):
        privacy = "Email opt-out"
    elif _to_bool(contact.get("DoNotCall")):
        privacy = "Do not call"

    return {
        "contact_id": contact_id,
        "first_name": contact.get("FirstName"),
        "last_name": contact.get("LastName"),
        "email": contact.get("Email"),
        "phone": contact.get("Phone"),
        "title": contact.get("Title"),
        "lead_source": contact.get("LeadSource"),
        "lead_stage": contact.get("Lead_Stage__c"),
        "owner_name": contact.get("Owner_Name"),
        "region": contact.get("region"),
        "confidence": _try_float(contact.get("confidence")),
        "intent_score": intent_score,
        "privacy": privacy,
        "account": account,
        "recent_activities": activities,
        "emails": [
            {
                "id": e.id,
                "direction": e.direction,
                "status": e.status,
                "to_email": e.to_email,
                "from_email": e.from_email,
                "subject": e.subject,
                "body": e.body,
                "created_at": e.created_at.isoformat() if e.created_at else None,
            }
            for e in emails
        ],
    }


def _rule_context(c: Dict[str, Any]) -> str:
    """Fallback user-facing context summary."""
    first = c.get("first_name") or "the contact"
    account = c.get("account") or {}
    activities = c.get("recent_activities", [])
    emails = c.get("emails", [])
    intent = c.get("intent_score", 0)

    activity_lines = []
    for a in activities[:3]:
        url = a.get("url") or "site"
        dur = a.get("duration_seconds") or 0
        mins = dur // 60
        activity_lines.append(f"{a.get('type')} on {url} ({mins}m {dur % 60}s)")

    email_lines = []
    for e in emails[:3]:
        email_lines.append(f"{e['direction']} email: {e['subject'] or '(no subject)'}")

    lines = [
        f"{first} {c.get('last_name') or ''} ({c.get('email')}) is a {c.get('title') or 'contact'} at {account.get('Name') or 'an unknown account'}.",
        f"Current lead stage: {c.get('lead_stage') or 'Open'}. Intent score: {intent}/100.",
        f"Privacy: {c.get('privacy')}. Region: {c.get('region') or 'unknown'}.",
    ]
    if activity_lines:
        lines.append("Recent activity: " + "; ".join(activity_lines))
    if email_lines:
        lines.append("Recent email activity: " + "; ".join(email_lines))
    if intent >= 90:
        lines.append("Very high intent — this contact should be prioritized for immediate outreach.")
    elif intent >= 70:
        lines.append("High intent — a timely follow-up is recommended.")
    elif intent >= 40:
        lines.append("Moderate intent — keep nurturing with relevant content.")
    else:
        lines.append("Low intent — focus on education and awareness.")

    return " ".join(lines)


def _generate_rule_learnings(c: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fallback AI-facing learning insights."""
    learnings: List[Dict[str, Any]] = []
    activities = c.get("recent_activities", [])
    emails = c.get("emails", [])
    intent = c.get("intent_score", 0)

    high_intent_pages = ["/pricing", "/demo", "/contact"]
    pages = [a.get("url") for a in activities if a.get("url")]
    high_pages = [p for p in pages if any(h in p for h in high_intent_pages)]

    if high_pages:
        learnings.append({
            "category": "intent_signal",
            "insight": f"Contact visits high-intent pages ({', '.join(high_pages[:3])}). Speed to lead is important.",
            "source": "visitoractivity",
            "confidence": min(95, intent + 5),
        })

    if len(activities) >= 3:
        learnings.append({
            "category": "intent_signal",
            "insight": "Multiple recent touchpoints indicate active evaluation.",
            "source": "visitoractivity",
            "confidence": min(90, intent),
        })

    if c.get("privacy") != "Can contact":
        learnings.append({
            "category": "policy_effectiveness",
            "insight": f"Privacy constraint: {c.get('privacy')}. Respect consent in all outreach.",
            "source": "system",
            "confidence": 99,
        })

    if any("case-studies" in (p or "") for p in pages):
        learnings.append({
            "category": "buying_signal",
            "insight": "Contact consumes social-proof content (case studies). Use customer stories in follow-up.",
            "source": "visitoractivity",
            "confidence": 85,
        })

    if intent >= 90:
        learnings.append({
            "category": "intent_signal",
            "insight": "Very high intent score. Recommend an immediate call/demo rather than email-only nurturing.",
            "source": "ai",
            "confidence": 95,
        })

    if emails:
        avg_len = sum(len((e.get("body") or "")) for e in emails) / len(emails)
        if avg_len < 150:
            learnings.append({
                "category": "writing_style",
                "insight": "Contact writes short, direct emails. Keep replies concise and actionable.",
                "source": "email",
                "confidence": 80,
                "sample_text": emails[0].get("body", "")[:200],
            })
        else:
            learnings.append({
                "category": "writing_style",
                "insight": "Contact writes detailed emails. Provide context and data in replies.",
                "source": "email",
                "confidence": 80,
                "sample_text": emails[0].get("body", "")[:200],
            })

    for e in emails:
        body = (e.get("body") or "").lower()
        if "price" in body or "pricing" in body or "cost" in body:
            learnings.append({
                "category": "buying_signal",
                "insight": "Contact asks about pricing/cost. Prepare pricing sheet and ROI talking points.",
                "source": "email",
                "confidence": 90,
                "sample_text": e.get("body", "")[:200],
            })
            break

    return learnings


def _llm_context(c: Dict[str, Any]) -> str:
    """Try to generate a richer context with the LLM. Falls back to rule-based on failure."""
    prompt = f"""You are a sales assistant. Write a concise, useful context summary (2-3 sentences) for a salesperson about this contact.
Use the data below. Highlight intent, recent activity, and the next best action.

Data:
{json.dumps(c, indent=2, default=str)}
"""
    try:
        return llm.gemini(prompt)
    except Exception as e:
        log.warning(f"LLM context generation failed: {e}; using rule-based context.")
        return _rule_context(c)


def _llm_learnings(c: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Try to generate AI learnings with the LLM. Falls back to rule-based on failure."""
    prompt = f"""You are an AI sales coach. Analyze the contact data and email history below.
Return ONLY a JSON array of learnings. Each item must have keys: category, insight, source, confidence (0-100), sample_text (optional).
Categories can be: writing_style, response_pattern, intent_signal, buying_signal, objection, policy_effectiveness, tone.

Data:
{json.dumps(c, indent=2, default=str)}
"""
    try:
        raw = llm.gemini_json(prompt)
        if isinstance(raw, list):
            return [dict(item) for item in raw]
        if isinstance(raw, dict) and "learnings" in raw:
            return [dict(item) for item in raw["learnings"]]
    except Exception as e:
        log.warning(f"LLM learning generation failed: {e}; using rule-based learnings.")

    return _generate_rule_learnings(c)


def ensure_contact_context(db: Session, contact_id: str, force: bool = False) -> ContactContext:
    """Get the latest user-facing ContactContext for a contact, generating it if missing or forced."""
    existing = (
        db.query(ContactContext)
        .filter(ContactContext.contact_id == contact_id, ContactContext.is_active == True)
        .order_by(ContactContext.created_at.desc())
        .first()
    )
    if existing and not force:
        return existing

    c = _build_contact_summary(db, contact_id)
    if not c:
        raise ValueError("Contact not found")

    # If there is no account in the summary, still set it under 'account' for rule_context
    summary = {"contact": c}
    content = _llm_context(c) if c.get("emails") or c.get("recent_activities") else _rule_context(c)

    ctx = ContactContext(
        contact_id=contact_id,
        context_type="ai_summary",
        content=content,
        generated_by="ai",
        priority=10,
        is_active=True,
    )
    db.add(ctx)
    db.commit()
    db.refresh(ctx)
    return ctx


def generate_learnings(db: Session, contact_id: str) -> List[Learning]:
    """Generate and store AI learnings for a contact, with extra depth for high-intent contacts."""
    c = _build_contact_summary(db, contact_id)
    if not c:
        raise ValueError("Contact not found")

    learnings = _llm_learnings(c) if c.get("emails") or c.get("recent_activities") or c["intent_score"] >= 90 else _generate_rule_learnings(c)

    # For very high intent, always add a few deep learning items
    if c["intent_score"] >= 90:
        deep = _deep_learnings(c)
        learnings.extend(deep)

    records: List[Learning] = []
    for item in learnings:
        record = Learning(
            contact_id=contact_id,
            category=item.get("category", "intent_signal"),
            source=item.get("source", "ai"),
            insight=item.get("insight", ""),
            sample_text=item.get("sample_text"),
            confidence=float(item.get("confidence", 0)),
            reviewed=False,
            applied_in_policy=None,
            extra_metadata={"generated_from": "learning_service", "intent_score": c["intent_score"]},
        )
        db.add(record)
        records.append(record)

    db.commit()
    for r in records:
        db.refresh(r)
    return records


def _deep_learnings(c: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Extra insights for contacts with intent >= 90."""
    insights = [{
        "category": "intent_signal",
        "insight": "Intent score above 90: this contact is in active buying mode. Prioritize over other leads.",
        "source": "ai",
        "confidence": 95,
    }]

    emails = c.get("emails", [])
    if emails:
        for e in emails:
            body = (e.get("body") or "").lower()
            if any(k in body for k in ["urgent", "asap", "this week", "tomorrow"]):
                insights.append({
                    "category": "buying_signal",
                    "insight": "Customer uses urgency language. Fast response time will improve close probability.",
                    "source": "email",
                    "confidence": 88,
                    "sample_text": e.get("body", "")[:200],
                })
                break

    activities = c.get("recent_activities", [])
    total_duration = sum((a.get("duration_seconds") or 0) for a in activities)
    if total_duration > 600:
        insights.append({
            "category": "buying_signal",
            "insight": f"Long total engagement time ({total_duration // 60}m). Strong signal of genuine interest.",
            "source": "visitoractivity",
            "confidence": 86,
        })

    return insights


def get_contact_contexts(db: Session, contact_id: str) -> List[ContactContext]:
    return (
        db.query(ContactContext)
        .filter(ContactContext.contact_id == contact_id, ContactContext.is_active == True)
        .order_by(ContactContext.priority.desc(), ContactContext.created_at.desc())
        .all()
    )


def get_contact_learnings(db: Session, contact_id: str, reviewed: Optional[bool] = None) -> List[Learning]:
    q = db.query(Learning).filter(Learning.contact_id == contact_id)
    if reviewed is not None:
        q = q.filter(Learning.reviewed == reviewed)
    return q.order_by(Learning.confidence.desc(), Learning.created_at.desc()).all()
