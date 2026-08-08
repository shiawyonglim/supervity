# app/routers/workbench.py
import logging
import threading
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.exception import Exception as ExceptionModel
from ..services.llm_service import llm
from ..services.audit import audit, AuditCategory, AuditSeverity
from ..services.email_service import send_email as send_email_via_smtp
from ..services.operators import MasterOrchestrator
from ..routers.contacts import _build_orchestrator_payload, _trigger_send_operator

log = logging.getLogger(__name__)
router = APIRouter(prefix="/workbench", tags=["Workbench Extended"])


class SlackBlockKitRequest(BaseModel):
    exception_id: int


@router.post("/slack/block-kit")
def generate_slack_block_kit(req: SlackBlockKitRequest, db: Session = Depends(get_db)):
    """Generate a Slack Block Kit JSON payload for an exception to allow human intervention via Slack."""
    exc = db.query(ExceptionModel).filter(ExceptionModel.id == req.exception_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")

    # Construct block kit JSON
    block_kit = {
        "blocks": [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 Exception: {exc.title}",
                    "emoji": True,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Type:* {exc.type}\n*Severity:* {exc.severity}\n*Description:* {exc.description}",
                },
            },
        ]
    }

    if exc.ai_recommendation:
        block_kit["blocks"].append(
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"🤖 *AI Recommendation ({exc.ai_confidence}%):*\n{exc.ai_recommendation}",
                },
            }
        )

    block_kit["blocks"].append(
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Approve Exception",
                        "emoji": True,
                    },
                    "style": "primary",
                    "value": f"approve_{exc.id}",
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Reject Exception",
                        "emoji": True,
                    },
                    "style": "danger",
                    "value": f"reject_{exc.id}",
                },
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View in Workbench",
                        "emoji": True,
                    },
                    "url": f"https://supervity.com/workbench?exception={exc.id}",
                },
            ],
        }
    )

    return {"block_kit": block_kit}


class AskAiRequest(BaseModel):
    exception_id: int


@router.post("/ask-ai")
def ask_ai_for_context(req: AskAiRequest, db: Session = Depends(get_db)):
    """Use Gemini to explain the exception context."""
    exc = db.query(ExceptionModel).filter(ExceptionModel.id == req.exception_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")

    prompt = f"""
    You are an AI assistant helping a human operator resolve a data exception.
    Explain what this exception means, why it might have happened, and what the operator should look out for.
    Keep it concise and helpful (max 3 sentences).

    Exception Details:
    Title: {exc.title}
    Description: {exc.description}
    Context Payload: {exc.context}
    """
    try:
        response = llm.gemini(prompt)
        return {"ai_context": response}
    except Exception as e:
        log.error(f"Ask AI error: {e}")
        raise HTTPException(status_code=500, detail="Failed to get AI context")


class DraftEmailRequest(BaseModel):
    contact_id: Optional[str] = None
    user_id: Optional[str] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    context: Optional[str] = None


@router.post("/draft-email")
def draft_email(req: DraftEmailRequest, db: Session = Depends(get_db)):
    """Draft an email using the Master Orchestrator when a contact is known, falling back to Gemini."""
    contact_id = req.contact_id or req.user_id

    if contact_id:
        try:
            payload, detail, _ = _build_orchestrator_payload(
                contact_id, db, include_detail=True
            )
            operator_result = MasterOrchestrator.process_lead(payload, timeout=8)

            if (
                isinstance(operator_result, dict)
                and "subject" in operator_result
                and "body" in operator_result
            ):
                return {
                    "contact_id": contact_id,
                    "subject": operator_result["subject"],
                    "draft": operator_result["body"],
                }

            log.warning(
                f"Master Orchestrator did not return a usable email draft: {operator_result}"
            )
        except Exception as e:
            log.warning(
                f"Workbench draft orchestrator failed ({e}); falling back to Gemini."
            )

    # Fallback to a simple Gemini prompt when no contact is found or the orchestrator is unavailable.
    prompt = f"""
    Draft a professional, friendly email to {req.user_name or 'there'} ({req.user_email or ''}).
    Context/Reason for email: {req.context or 'General check-in'}

    Return ONLY the email body (no subject line unless you format it clearly).
    """
    try:
        body = llm.gemini(prompt)
        return {
            "contact_id": contact_id,
            "subject": req.context or "Follow-up",
            "draft": body,
        }
    except Exception as e:
        log.error(f"Draft email error: {e}")
        raise HTTPException(status_code=500, detail="Failed to draft email")


class SendEmailRequest(BaseModel):
    to: Optional[str] = None
    subject: str
    body: str
    contact_id: Optional[str] = None


@router.post("/send-email")
def send_email(req: SendEmailRequest, db: Session = Depends(get_db)):
    """Send an email and, when a contact is referenced, hand the full lead payload to the Master Orchestrator."""
    to_email = req.to
    contact_id = req.contact_id

    if not to_email and not contact_id:
        raise HTTPException(
            status_code=400, detail="Provide either 'to' or 'contact_id'."
        )

    if contact_id:
        contact = (
            db.execute(
                text(
                    'SELECT "Id", "FirstName", "LastName", "Email" FROM contact WHERE "Id" = :id'
                ),
                {"id": contact_id},
            )
            .mappings()
            .first()
        )
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
        to_email = to_email or contact.get("Email")

    if not to_email:
        raise HTTPException(status_code=400, detail="No recipient email available.")

    success = send_email_via_smtp(
        to_email, req.subject, req.body, contact_id=contact_id
    )

    # Always hand the send action to the Master Orchestrator when a contact is known,
    # using the same enriched lead payload as the dashboard send flow.
    if contact_id:
        contact_dict = dict(contact) if contact else {}
        threading.Thread(
            target=_trigger_send_operator,
            args=(contact_id, req.subject, req.body, contact_dict),
            daemon=True,
        ).start()

    status = "sent" if success else "queued"
    audit.log_sync(
        action="communications.send_email",
        description=f"{status.capitalize()} email to {to_email} with subject '{req.subject}'",
        category=AuditCategory.DATA,
        severity=AuditSeverity.INFO,
        resource_type="email" if not contact_id else "contact",
        resource_name=req.subject,
        resource_id=contact_id,
        metadata={
            "to": to_email,
            "subject": req.subject,
            "body_preview": req.body[:200],
            "smtp_success": success,
            "contact_id": contact_id,
        },
        actor={"id": "workbench", "email": "workbench@supervity.ai"},
    )
    return {
        "status": status,
        "to": to_email,
        "subject": req.subject,
        "smtp_success": success,
        "contact_id": contact_id,
    }
