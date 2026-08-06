# app/routers/operators.py
"""
Endpoints for the Supervity AI Operators pipeline.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, List

from ..services.operators import run_operator_pipeline_batch

router = APIRouter(prefix="/operators", tags=["AI Operators"])

class LeadTrigger(BaseModel):
    lead_id: str
    name: str
    email: EmailStr
    company: Optional[str] = ""
    inquiry_text: str
    source: Optional[str] = ""

@router.post("/batch")
def process_lead_batch(leads: List[LeadTrigger]):
    """
    Trigger the 5-step AI Operator pipeline for a batch of leads.
    Pushes data back to Supervity iteratively.
    """
    try:
        raw_payloads = [lead.model_dump() for lead in leads]
        results = run_operator_pipeline_batch(raw_payloads)
        return {"status": "success", "processed": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
