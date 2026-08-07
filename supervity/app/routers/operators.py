# app/routers/operators.py
"""
Endpoints for the Supervity AI Operators pipeline.
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any

from ..services.operators import run_operator_pipeline_batch, MasterOrchestrator

router = APIRouter(prefix="/operators", tags=["AI Operators"])

@router.post("/process")
def process_single_lead(payload: Dict[str, Any]):
    """
    Trigger the 5-step AI Operator pipeline for a single lead.
    (This matches the new Supervity JSON schema exactly).
    """
    try:
        result = MasterOrchestrator.process_lead(payload)
        return {"status": "success", "result": result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/batch")
def process_lead_batch(leads: List[Dict[str, Any]]):
    """
    Trigger the 5-step AI Operator pipeline for a batch of leads.
    """
    try:
        results = run_operator_pipeline_batch(leads)
        return {"status": "success", "processed": len(results), "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
