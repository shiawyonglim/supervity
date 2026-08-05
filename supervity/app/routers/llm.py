# app/routers/llm.py
"""
LLM API endpoints — test and use the dual-model LLM service.
"""

import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ..services.llm_service import llm

log = logging.getLogger(__name__)

router = APIRouter(prefix="/llm", tags=["LLM"])


# ── Request / Response Schemas ──────────────────────────────────────────

class LLMRequest(BaseModel):
    prompt: str
    system_prompt: str | None = None


class LLMResponse(BaseModel):
    model: str
    response: str | dict | list


# ── Endpoints ───────────────────────────────────────────────────────────

@router.get("/status")
def llm_status():
    """Check which LLM backends are available."""
    return llm.status()


@router.post("/nemotron", response_model=LLMResponse)
def call_nemotron(req: LLMRequest):
    """
    Send a prompt to NVIDIA Nemotron 550B (via NIM).
    Best for: AI Policy parsing, complex reasoning.
    """
    try:
        system = req.system_prompt or "You are an enterprise AI policy engine. Always respond with valid JSON only."
        result = llm.nemotron(prompt=req.prompt, system_prompt=system)
        return LLMResponse(model="nvidia/nemotron-3-ultra-550b-a55b", response=result)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        log.error(f"Nemotron error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gemini", response_model=LLMResponse)
def call_gemini(req: LLMRequest):
    """
    Send a prompt to Google Gemini.
    Best for: AI Insights, data analytics, large context analysis.
    """
    try:
        result = llm.gemini(prompt=req.prompt)
        return LLMResponse(model="gemini-2.0-flash", response=result)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        log.error(f"Gemini error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/gemini/json", response_model=LLMResponse)
def call_gemini_json(req: LLMRequest):
    """
    Send a prompt to Google Gemini with strict JSON output mode.
    Best for: Structured data extraction.
    """
    try:
        result = llm.gemini_json(prompt=req.prompt)
        return LLMResponse(model="gemini-2.0-flash (JSON mode)", response=result)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        log.error(f"Gemini JSON error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
