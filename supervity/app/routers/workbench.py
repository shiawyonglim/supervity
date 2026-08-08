# app/routers/workbench.py
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.exception import Exception as ExceptionModel
from ..services.llm_service import llm
from ..services.audit import audit, AuditCategory, AuditSeverity
from ..services.email_service import send_email as send_email_via_smtp

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
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Type:* {exc.type}\n*Severity:* {exc.severity}\n*Description:* {exc.description}"
                }
            }
        ]
    }

    if exc.ai_recommendation:
        block_kit["blocks"].append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🤖 *AI Recommendation ({exc.ai_confidence}%):*\n{exc.ai_recommendation}"
            }
        })

    block_kit["blocks"].append({
        "type": "actions",
        "elements": [
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Approve Exception",
                    "emoji": True
                },
                "style": "primary",
                "value": f"approve_{exc.id}"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Reject Exception",
                    "emoji": True
                },
                "style": "danger",
                "value": f"reject_{exc.id}"
            },
            {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "View in Workbench",
                    "emoji": True
                },
                "url": f"https://supervity.com/workbench?exception={exc.id}"
            }
        ]
    })

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
    user_id: str
    user_name: str
    user_email: str
    context: Optional[str] = None

@router.post("/draft-email")
def draft_email(req: DraftEmailRequest):
    """Use Gemini to draft an email to a user."""
    prompt = f"""
    Draft a professional, friendly email to {req.user_name} ({req.user_email}).
    Context/Reason for email: {req.context or 'General check-in'}
    
    Return ONLY the email body (no subject line unless you format it clearly).
    """
    try:
        response = llm.gemini(prompt)
        return {"draft": response}
    except Exception as e:
        log.error(f"Draft email error: {e}")
        raise HTTPException(status_code=500, detail="Failed to draft email")


class SendEmailRequest(BaseModel):
    to: str
    subject: str
    body: str


@router.post("/send-email")
def send_email(req: SendEmailRequest):
    """Send an email using the EmailService."""
    success = send_email_via_smtp(req.to, req.subject, req.body)
    
    if success:
        audit.log_sync(
            action="communications.send_email",
            description=f"Sent email to {req.to} with subject '{req.subject}'",
            category=AuditCategory.DATA,
            severity=AuditSeverity.INFO,
            resource_type="email",
            resource_name=req.subject,
            metadata={"to": req.to, "subject": req.subject, "body_preview": req.body[:200]},
            actor={"id": "workbench", "email": "workbench@supervity.ai"},
        )
        return {"status": "sent", "to": req.to, "subject": req.subject}
    else:
        raise HTTPException(status_code=500, detail="Failed to send email. Check credentials.")
