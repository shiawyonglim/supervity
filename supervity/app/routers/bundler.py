# app/routers/bundler.py
"""
Endpoints for the Supervity Data Bundler.
"""

from fastapi import APIRouter, HTTPException
from ..services.bundler import bundle_and_push_data

router = APIRouter(prefix="/bundler", tags=["Data Bundler"])

@router.post("/run")
def run_bundler_job(limit: int = 10, mode: str = "direct"):
    """
    Trigger the Data Bundler.
    mode = 'direct' (sends full JSON payloads to orchestrator)
    mode = 'supabase' (sends just prospect_ids to orchestrator)
    """
    try:
        result = bundle_and_push_data(limit=limit, mode=mode)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
