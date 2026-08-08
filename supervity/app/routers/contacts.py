# app/routers/contacts.py
"""Endpoints for User Communications and email drafting in Workbench."""

import logging
import threading
from typing import List, Optional, Any
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..core.database import get_db
from ..services.audit import audit, AuditCategory, AuditSeverity
from ..services.operators import MasterOrchestrator
from ..services.learning_service import ensure_contact_context, generate_learnings, get_contact_contexts, get_contact_learnings
from ..services.email_service import send_email as send_email_via_smtp

log = logging.getLogger(__name__)

router = APIRouter(prefix="/contacts", tags=["Contacts & Communications"])

class ContactRead(BaseModel):
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    title: Optional[str] = None
    account_name: Optional[str] = None
    lead_stage: Optional[str] = None
    owner_name: Optional[str] = None


class AccountDetail(BaseModel):
    id: str
    name: Optional[str] = None
    industry: Optional[str] = None
    number_of_employees: Optional[int] = None
    type: Optional[str] = None
    website: Optional[str] = None
    billing_country: Optional[str] = None
    strategic: Optional[bool] = None


class VisitorActivity(BaseModel):
    id: int
    visitor_id: Optional[str] = None
    type: Optional[str] = None
    created_at: Optional[str] = None
    url: Optional[str] = None
    duration_seconds: Optional[int] = None
    campaign: Optional[str] = None
    source: Optional[str] = None
    company_domain: Optional[str] = None
    channel: Optional[str] = None


class EmailRead(BaseModel):
    id: int
    subject: str
    body: str
    sent_at: str
    sent_by: str


class ContactDetail(BaseModel):
    id: str
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    title: Optional[str] = None
    lead_source: Optional[str] = None
    lead_stage: Optional[str] = None
    owner_name: Optional[str] = None
    owner_id: Optional[str] = None
    has_opted_out_of_email: bool = False
    do_not_call: bool = False
    consent_basis: Optional[str] = None
    region: Optional[str] = None
    confidence: Optional[float] = None
    created_date: Optional[str] = None
    last_activity_date: Optional[str] = None
    account: Optional[AccountDetail] = None
    recent_activities: List[VisitorActivity] = []
    emails: List[EmailRead] = []
    intent_score: int = 0
    intent_signals: List[str] = []
    privacy_status: str = "Can contact"

class EmailDraftRequest(BaseModel):
    prompt_context: Optional[str] = None
    role: Optional[str] = None
    lead_stage: Optional[str] = None
    intent_score: Optional[int] = None
    intent_signals: Optional[List[str]] = None

class EmailDraftResponse(BaseModel):
    subject: str
    body: str

@router.get("", response_model=List[ContactRead])
def list_contacts(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all contacts for the Workbench Communications view."""
    query = text("""
        SELECT 
            c."Id" as id, 
            c."FirstName" as first_name, 
            c."LastName" as last_name, 
            c."Email" as email, 
            c."Title" as title, 
            a."Name" as account_name, 
            c."Lead_Stage__c" as lead_stage,
            c."Owner_Name" as owner_name
        FROM contact c
        LEFT JOIN account a ON c."AccountId" = a."Id"
        ORDER BY c."CreatedDate" DESC NULLS LAST, c."Id" DESC
        OFFSET :skip LIMIT :limit
    """)
    rows = db.execute(query, {"skip": skip, "limit": limit}).mappings().all()
    return [dict(r) for r in rows]


def _to_bool(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("true", "1", "yes", "t")


def _compute_intent(contact: dict, activities: List[dict]) -> tuple[int, List[str], str]:
    """Compute a 0-100 intent score and human-readable signals from confidence + visitor activity."""
    signals: List[str] = []

    try:
        base = float(contact.get("confidence") or 0) * 100
    except (ValueError, TypeError):
        base = 50.0

    score = base

    # Lead source intent
    source = (contact.get("LeadSource") or "").lower()
    if "pricing" in source or "demo" in source or "contact" in source:
        score += 20
        signals.append("High-intent lead source")
    elif "referral" in source or "trade" in source:
        score += 15
        signals.append("Warm referral / event lead")
    elif "content" in source or "webinar" in source or "newsletter" in source:
        score += 8
        signals.append("Inbound content engagement")

    stage = (contact.get("Lead_Stage__c") or "").lower()
    if stage in ("sql", "opportunity", "customer"):
        score += 15
        signals.append("Advanced pipeline stage")

    for a in activities:
        url = (a.get("url") or "").lower()
        dur = a.get("duration_seconds") or 0
        act_type = (a.get("type") or "").lower()

        if url in ("/pricing", "/demo", "/contact"):
            score += 15
            signals.append(f"Visited high-intent page {url}")
        elif url in ("/case-studies",):
            score += 10
            signals.append("Downloaded/read case study")
        elif url and url != "/":
            score += 5
            signals.append(f"Visited {url}")

        if act_type in ("download", "click"):
            score += 5

        if dur and dur > 60:
            score += 5
        if dur and dur > 300:
            score += 5

    # Recent activity density
    if len(activities) >= 3:
        signals.append("Multiple recent touch points")
        score += 10

    # Cap and round
    score = max(0, min(100, round(score)))

    # Privacy status
    opted_out = _to_bool(contact.get("HasOptedOutOfEmail"))
    do_not_call = _to_bool(contact.get("DoNotCall"))
    consent = (contact.get("consent_basis") or "").lower()
    if opted_out and do_not_call:
        privacy = "Do not email or call"
    elif opted_out:
        privacy = "Email opt-out"
    elif do_not_call:
        privacy = "Do not call"
    elif consent in ("opt_out", "no_consent"):
        privacy = "Consent not given"
    else:
        privacy = "Can contact"

    return score, list(set(signals))[:6], privacy


def _build_contact_detail(contact: dict, account: Optional[dict], activities: List[dict], emails: List[dict]) -> dict:
    intent_score, intent_signals, privacy = _compute_intent(contact, activities)

    return {
        "id": contact.get("Id"),
        "first_name": contact.get("FirstName"),
        "last_name": contact.get("LastName"),
        "email": contact.get("Email"),
        "phone": str(contact.get("Phone")) if contact.get("Phone") is not None else None,
        "title": contact.get("Title"),
        "lead_source": contact.get("LeadSource"),
        "lead_stage": contact.get("Lead_Stage__c"),
        "owner_name": contact.get("Owner_Name"),
        "owner_id": contact.get("OwnerId"),
        "has_opted_out_of_email": _to_bool(contact.get("HasOptedOutOfEmail")),
        "do_not_call": _to_bool(contact.get("DoNotCall")),
        "consent_basis": contact.get("consent_basis"),
        "region": contact.get("region"),
        "confidence": _try_float(contact.get("confidence")),
        "created_date": contact.get("CreatedDate"),
        "last_activity_date": contact.get("LastActivityDate"),
        "account": {
            "id": account.get("Id") if account else None,
            "name": account.get("Name") if account else None,
            "industry": account.get("Industry") if account else None,
            "number_of_employees": _try_int(account.get("NumberOfEmployees")) if account else None,
            "type": account.get("Type") if account else None,
            "website": account.get("Website") if account else None,
            "billing_country": account.get("BillingCountry") if account else None,
            "strategic": _to_bool(account.get("Strategic__c")) if account else None,
        } if account else None,
        "recent_activities": [
            {
                "id": a.get("id"),
                "visitor_id": a.get("visitor_id"),
                "type": a.get("type"),
                "created_at": a.get("created_at"),
                "url": a.get("url"),
                "duration_seconds": _try_int(a.get("duration_seconds")),
                "campaign": a.get("campaign"),
                "source": a.get("source"),
                "company_domain": a.get("company_domain"),
                "channel": a.get("channel"),
            }
            for a in activities
        ],
        "emails": emails,
        "intent_score": intent_score,
        "intent_signals": intent_signals,
        "privacy_status": privacy,
    }


def _try_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _try_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


@router.get("/{contact_id}", response_model=ContactDetail)
def get_contact_detail(contact_id: str, db: Session = Depends(get_db)):
    """Get full contact details, account, visitor activity, intent score and email history."""
    contact = db.execute(text('SELECT * FROM contact WHERE "Id" = :id'), {"id": contact_id}).mappings().first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
    contact = dict(contact)

    account = None
    if contact.get("AccountId"):
        account = db.execute(text('SELECT * FROM account WHERE "Id" = :id'), {"id": contact["AccountId"]}).mappings().first()
        if account:
            account = dict(account)

    activities = db.execute(
        text('SELECT * FROM visitoractivity WHERE prospect_id = :id ORDER BY created_at DESC LIMIT 10'),
        {"id": contact_id}
    ).mappings().all()
    activities = [dict(a) for a in activities]

    emails = _mock_emails(contact)
    return _build_contact_detail(contact, account, activities, emails)


def _mock_emails(contact: dict) -> List[dict]:
    first_name = contact.get("FirstName") or "there"
    stage = contact.get("Lead_Stage__c") or "Open"
    emails = [
        {
            "id": 1,
            "subject": f"Following up on your visit, {first_name}",
            "body": f"Hi {first_name},\n\nI noticed you were checking out our pricing page recently. I'd love to connect and see if we can help your team.\n\nBest,\nSales Team",
            "sent_at": "2026-08-01T10:00:00Z",
            "sent_by": "Automated Sequence",
        }
    ]
    if stage in ["SQL", "Opportunity", "Customer"]:
        emails.append({
            "id": 2,
            "subject": "Proposal details",
            "body": f"Hi {first_name},\n\nThanks for the great call yesterday. Attached is the proposal we discussed.\n\nLet me know if you have any questions.\n\nBest,\nAccount Executive",
            "sent_at": "2026-08-05T14:30:00Z",
            "sent_by": "Account Executive",
        })
    return emails


@router.get("/{contact_id}/emails", response_model=List[EmailRead])
def get_contact_emails(contact_id: str, db: Session = Depends(get_db)):
    """Get mock email history for a contact."""
    # Since we don't have a real email table, we'll mock some past emails based on their lead stage.
    contact_query = text('SELECT "FirstName", "Lead_Stage__c" FROM contact WHERE "Id" = :id')
    contact = db.execute(contact_query, {"id": contact_id}).mappings().first()
    
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")
        
    first_name = contact.get("FirstName") or "there"
    stage = contact.get("Lead_Stage__c") or "Open"
    
    # Generate some mock emails
    emails = [
        {
            "id": 1,
            "subject": f"Following up on your visit, {first_name}",
            "body": f"Hi {first_name},\n\nI noticed you were checking out our pricing page recently. I'd love to connect and see if we can help your team.\n\nBest,\nSales Team",
            "sent_at": "2026-08-01T10:00:00Z",
            "sent_by": "Automated Sequence"
        }
    ]
    
    if stage in ["SQL", "Opportunity", "Customer"]:
        emails.append({
            "id": 2,
            "subject": "Proposal details",
            "body": f"Hi {first_name},\n\nThanks for the great call yesterday. Attached is the proposal we discussed.\n\nLet me know if you have any questions.\n\nBest,\nAccount Executive",
            "sent_at": "2026-08-05T14:30:00Z",
            "sent_by": "Account Executive"
        })
        
    return emails

def _fallback_email(detail: dict, role_label: str, lead_stage: str, intent_score: int, activities: List[dict]) -> EmailDraftResponse:
    """Build a context-aware fallback email when the LLM is unavailable or rate-limited."""
    first_name = detail.get("first_name") or "there"
    account_name = detail.get("account", {}).get("name") or detail.get("account_name") or "your company"
    lead_stage = lead_stage or "Open"

    # Pick the most interesting recent activity
    top_activity = None
    top_score = -1
    for a in activities:
        url = (a.get("url") or "").lower()
        score = 0
        if url in ("/pricing", "/demo", "/contact"):
            score = 30
        elif "/case-studies" in url:
            score = 20
        elif url and url != "/":
            score = 10
        dur = a.get("duration_seconds") or 0
        score += min(dur // 60, 10)
        if score > top_score:
            top_score = score
            top_activity = a

    activity_line = ""
    if top_activity:
        act_type = top_activity.get("type") or "visit"
        url = top_activity.get("url") or "our site"
        if url in ("/pricing",):
            activity_line = f"I noticed you spent some time on our pricing page ({top_activity.get('duration_seconds') or 0}s). I'd love to share how teams like {account_name} use Supervity to speed up revenue workflows."
        elif url in ("/demo",):
            activity_line = "I saw you were looking at our demo — let me know if you'd like a personalized walkthrough."
        elif url in ("/contact",):
            activity_line = "Thanks for reaching out via our contact page. I'm here to help."
        elif "/case-studies" in url:
            activity_line = "I saw you checked out one of our case studies. I can share more relevant success stories for your industry."
        else:
            activity_line = f"I noticed your recent {act_type.lower()} on {url}. I'd love to connect and see if Supervity can help {account_name}."
    else:
        activity_line = f"I wanted to reach out because {account_name} looks like a great fit for Supervity."

    tone = "helpful"
    cta = "Does a quick 15-minute call this week work for you?"
    if lead_stage.lower() in ("sql", "opportunity"):
        tone = "direct"
        cta = "Can we schedule a 20-minute call to discuss next steps?"
    elif lead_stage.lower() == "mql" and intent_score >= 60:
        tone = "curious and direct"
        cta = "Are you open to a quick call this week to explore how Supervity fits your team?"
    elif lead_stage.lower() == "open" and intent_score >= 60:
        tone = "helpful and direct"
        cta = "I'd love to share a quick 2-minute demo — does a 15-minute call this week work?"

    privacy_note = ""
    if detail.get("do_not_call"):
        privacy_note = " (email preferred)"

    body = f"Hi {first_name},\n\n{activity_line}\n\nGiven your {lead_stage} stage and the activity above, I thought a {tone} note from the Supervity team would be useful.{privacy_note}\n\n{cta}\n\nBest,\n{role_label} at Supervity"

    subject = f"Following up on your {top_activity.get('url', 'visit') if top_activity else 'recent visit'} — Supervity"
    return EmailDraftResponse(subject=subject, body=body)


@router.post("/{contact_id}/draft", response_model=EmailDraftResponse)
def draft_email(contact_id: str, req: EmailDraftRequest, db: Session = Depends(get_db)):
    """Draft a highly personalized Supervity sales email to the contact."""
    try:
        contact = db.execute(text('SELECT * FROM contact WHERE "Id" = :id'), {"id": contact_id}).mappings().first()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        contact = dict(contact)

        account = None
        if contact.get("AccountId"):
            account = db.execute(text('SELECT * FROM account WHERE "Id" = :id'), {"id": contact["AccountId"]}).mappings().first()
            if account:
                account = dict(account)

        activities = db.execute(
            text('SELECT * FROM visitoractivity WHERE prospect_id = :id ORDER BY created_at DESC LIMIT 8'),
            {"id": contact_id}
        ).mappings().all()
        activities = [dict(a) for a in activities]

        emails = _mock_emails(contact)
        detail = _build_contact_detail(contact, account, activities, emails)

        role_label = req.role or "sales representative"
        lead_stage = req.lead_stage or detail["lead_stage"] or "Open"
        intent_score = req.intent_score or detail["intent_score"]
        intent_signals = req.intent_signals or detail["intent_signals"]

        privacy_block = ""
        if detail["has_opted_out_of_email"]:
            privacy_block = "CRITICAL: This contact has opted out of email. Return a note explaining no email can be sent."
        elif detail["do_not_call"]:
            privacy_block = "Note: Do not call this contact. Email only."

        lead_payload = {
            "prospect_id": contact_id,
            "sender": "Supervity",
            "sender_role": role_label,
            "contact": detail,
            "lead_stage": lead_stage,
            "intent_score": intent_score,
            "intent_signals": intent_signals,
            "privacy_constraints": privacy_block or "Can email and call.",
            "recent_activities": detail["recent_activities"],
            "account": detail["account"],
            "recent_email_history": detail["emails"],
            "additional_instructions": req.prompt_context,
        }

        try:
            # Call the Master Orchestrator with a short timeout so the user isn't
            # left waiting if the workflow is slow or unavailable.
            operator_result = MasterOrchestrator.process_lead(lead_payload, timeout=8)

            if isinstance(operator_result, dict) and "subject" in operator_result and "body" in operator_result:
                return EmailDraftResponse(
                    subject=operator_result["subject"],
                    body=operator_result["body"],
                )

            log.warning(f"Master Orchestrator did not return a usable email draft: {operator_result}")
            return _fallback_email(detail, role_label, lead_stage, intent_score, activities)
        except Exception as e:
            log.warning(f"Master Orchestrator failed ({e}); falling back to rule-based draft.")
            return _fallback_email(detail, role_label, lead_stage, intent_score, activities)
    except Exception as e:
        log.error(f"Email draft error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class EmailSendRequest(BaseModel):
    subject: str
    body: str


def _trigger_send_operator(contact_id: str, subject: str, body: str, contact: dict):
    """Fire the Master Orchestrator in the background so sending an email is handed to the Supervity Auto workflow."""
    payload = {
        "prospect_id": contact_id,
        "action": "send_email",
        "contact": contact,
        "email": {"subject": subject, "body": body},
    }
    try:
        result = MasterOrchestrator.process_lead(payload)
        log.info(f"Send operator result for {contact_id}: {result}")
    except Exception as e:
        log.error(f"Send operator failed for {contact_id}: {e}")


@router.post("/{contact_id}/send-email")
def send_email(contact_id: str, req: EmailSendRequest, db: Session = Depends(get_db)):
    """Send an email using Outlook SMTP in addition to tracking."""
    contact = db.execute(text('SELECT "Id", "FirstName", "LastName", "Email" FROM contact WHERE "Id" = :id'), {"id": contact_id}).mappings().first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    contact_dict = dict(contact)
    to_email = contact_dict.get('Email', '')

    if not to_email:
        raise HTTPException(status_code=400, detail="Contact has no email address")

    success = send_email_via_smtp(to_email, req.subject, req.body, contact_id=contact_id)

    # Always hand the send action to the Master Orchestrator so the AI workflow can
    # augment delivery, log context, or trigger downstream actions.
    threading.Thread(
        target=_trigger_send_operator,
        args=(contact_id, req.subject, req.body, contact_dict),
        daemon=True,
    ).start()

    status = "sent" if success else "queued"
    audit.log_sync(
        action="communications.send_email",
        description=f"{status.capitalize()} email to {contact_dict.get('FirstName', '')} {contact_dict.get('LastName', '')} ({to_email})",
        category=AuditCategory.DATA,
        severity=AuditSeverity.INFO,
        resource_type="contact",
        resource_id=contact_id,
        metadata={"subject": req.subject, "body_preview": req.body[:200], "smtp_success": success},
        actor={"id": "sales-dashboard", "email": "sales-dashboard@supervity.ai"},
    )
    return {"status": status, "to": to_email, "smtp_success": success}


@router.get("/{contact_id}/context")
def get_context(contact_id: str, db: Session = Depends(get_db)):
    """Return user-facing context snippets for a contact, generating one if missing."""
    try:
        ensure_contact_context(db, contact_id)
        contexts = get_contact_contexts(db, contact_id)
        return {
            "contact_id": contact_id,
            "contexts": [
                {
                    "id": c.id,
                    "type": c.context_type,
                    "content": c.content,
                    "generated_by": c.generated_by,
                    "priority": c.priority,
                    "created_at": c.created_at,
                }
                for c in contexts
            ],
        }
    except Exception as e:
        log.error(f"Context error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{contact_id}/learn")
def learn_contact(contact_id: str, db: Session = Depends(get_db)):
    """Generate AI learnings for a contact, with extra depth for high-intent contacts."""
    try:
        learnings = generate_learnings(db, contact_id)
        # Also refresh the user-facing context after learning
        ensure_contact_context(db, contact_id, force=True)
        return {
            "contact_id": contact_id,
            "generated": len(learnings),
            "learnings": [
                {
                    "id": l.id,
                    "category": l.category,
                    "insight": l.insight,
                    "source": l.source,
                    "confidence": l.confidence,
                    "sample_text": l.sample_text,
                    "reviewed": l.reviewed,
                }
                for l in learnings
            ],
        }
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        log.error(f"Learning error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{contact_id}/learnings")
def get_learnings(contact_id: str, db: Session = Depends(get_db)):
    """Return stored AI learnings for a contact."""
    return {
        "contact_id": contact_id,
        "learnings": [
            {
                "id": l.id,
                "category": l.category,
                "insight": l.insight,
                "source": l.source,
                "confidence": l.confidence,
                "sample_text": l.sample_text,
                "reviewed": l.reviewed,
            }
            for l in get_contact_learnings(db, contact_id)
        ],
    }


class StageUpdateRequest(BaseModel):
    lead_stage: str


@router.put("/{contact_id}/stage")
def update_lead_stage(contact_id: str, req: StageUpdateRequest, db: Session = Depends(get_db)):
    """Update a contact's lead stage and log the change."""
    contact = db.execute(text('SELECT "Id", "FirstName", "LastName", "Lead_Stage__c", "Email" FROM contact WHERE "Id" = :id'), {"id": contact_id}).mappings().first()
    if not contact:
        raise HTTPException(status_code=404, detail="Contact not found")

    old_stage = contact.get("Lead_Stage__c") or "Open"
    new_stage = req.lead_stage

    db.execute(
        text('UPDATE contact SET "Lead_Stage__c" = :stage WHERE "Id" = :id'),
        {"stage": new_stage, "id": contact_id},
    )
    db.commit()

    audit.log_sync(
        action="contact.stage_change",
        description=f"Changed lead stage for {contact.get('FirstName', '')} {contact.get('LastName', '')} from {old_stage} to {new_stage}",
        category=AuditCategory.DATA,
        severity=AuditSeverity.INFO,
        resource_type="contact",
        resource_id=contact_id,
        metadata={"old_stage": old_stage, "new_stage": new_stage},
        actor={"id": "sales-dashboard", "email": "sales-dashboard@supervity.ai"},
    )

    return {
        "contact_id": contact_id,
        "old_stage": old_stage,
        "new_stage": new_stage,
    }
