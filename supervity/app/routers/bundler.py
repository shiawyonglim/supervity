# app/routers/bundler.py
"""
Endpoints for the Supervity Data Bundler.
"""

from fastapi import APIRouter, HTTPException
from ..services.bundler import bundle_and_push_data

router = APIRouter(prefix="/bundler", tags=["Data Bundler"])

@router.post("/run")
def run_bundler_job(limit: int = 10):
    """
    Trigger the Data Bundler to read VisitorActivity, enrich it with Contact/Account data,
    and push the bundled JSON to the Supervity Visual Workflow platform.
    """
    try:
        result = bundle_and_push_data(limit=limit)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
