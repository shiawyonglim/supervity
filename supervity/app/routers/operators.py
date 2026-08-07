# app/routers/operators.py
"""
Endpoints for the Supervity AI Operators pipeline.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, EmailStr
from sqlalchemy import text
from typing import Optional, List, Dict, Any

from ..core.database import get_db
from ..services.operators import run_operator_pipeline_batch, MasterOrchestrator
from sqlalchemy.orm import Session

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


@router.post("/run-all")
def run_operators_on_all_contacts(db: Session = Depends(get_db), batch_size: int = 50):
    """
    Loop through every contact in the database and run the 5-step operator pipeline.
    Processes in batches to avoid overloading the external workflow.
    """
    try:
        rows = db.execute(
            text(
                'SELECT "Id", "FirstName", "LastName", "Email", "Title", "AccountId", "Lead_Stage__c" '
                'FROM contact ORDER BY "Id"'
            )
        ).mappings().all()

        payloads = [
            {
                "prospect_id": str(r["Id"]),
                "first_name": r["FirstName"] or "",
                "last_name": r["LastName"] or "",
                "email": r["Email"] or "",
                "title": r["Title"] or "",
                "account_id": r["AccountId"] or "",
                "lead_stage": r["Lead_Stage__c"] or "Open",
            }
            for r in rows
        ]

        results = []
        errors = 0
        for i in range(0, len(payloads), batch_size):
            batch = payloads[i : i + batch_size]
            batch_results = run_operator_pipeline_batch(batch)
            for res in batch_results:
                if res.get("error") or res.get("status") == "error":
                    errors += 1
            results.extend(batch_results)

        return {
            "status": "success",
            "total_contacts": len(rows),
            "batches": (len(rows) + batch_size - 1) // batch_size,
            "errors": errors,
            "results": results,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
