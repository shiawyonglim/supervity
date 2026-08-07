# app/routers/contacts.py
"""Endpoints for User Communications and email drafting in Workbench."""

import logging
from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import text
from sqlalchemy.orm import Session
from pydantic import BaseModel

from ..core.database import get_db
from ..services.llm_service import llm

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

class EmailRead(BaseModel):
    id: int
    subject: str
    body: str
    sent_at: str
    sent_by: str

class EmailDraftRequest(BaseModel):
    prompt_context: Optional[str] = None

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

@router.post("/{contact_id}/draft", response_model=EmailDraftResponse)
def draft_email(contact_id: str, req: EmailDraftRequest, db: Session = Depends(get_db)):
    """Draft an email to the contact using LLM."""
    try:
        # Fetch full context
        contact = db.execute(text('SELECT * FROM contact WHERE "Id" = :id'), {"id": contact_id}).mappings().first()
        if not contact:
            raise HTTPException(status_code=404, detail="Contact not found")
            
        account = None
        if contact.get("AccountId"):
            account = db.execute(text('SELECT * FROM account WHERE "Id" = :id'), {"id": contact.get("AccountId")}).mappings().first()
            
        activities = db.execute(text('SELECT type, url, created_at, duration_seconds FROM visitoractivity WHERE prospect_id = :id ORDER BY created_at DESC LIMIT 5'), {"id": contact_id}).mappings().all()
        
        context_data = {
            "contact": dict(contact),
            "account": dict(account) if account else None,
            "recent_activities": [dict(a) for a in activities],
            "additional_instructions": req.prompt_context
        }
        
        prompt = """You are an expert sales representative. Draft a highly personalized email to this contact based on their data.
Make it sound human, professional, and relevant to their recent activities (e.g. pages they visited).

Return ONLY a JSON object with two keys:
- subject: A catchy email subject
- body: The body of the email (using plain text with newlines \\n)

Here is the data:
"""
        
        result = llm.gemini_json(prompt=prompt, data=context_data)
        
        return EmailDraftResponse(
            subject=result.get("subject", "Following up"),
            body=result.get("body", "Hi there,\n\nI wanted to reach out...")
        )
    except Exception as e:
        log.error(f"Email draft error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
