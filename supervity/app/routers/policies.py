# app/routers/policies.py
"""AI Policies CRUD + AI-powered endpoints — business rules that constrain the AI agents."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.policy import Policy as PolicyModel
from ..schemas.policy import Policy, PolicyCreate, PolicyGenerateRequest, PolicyUpdate
from ..services.llm_service import llm
from ..services import policy_engine

log = logging.getLogger(__name__)

router = APIRouter(prefix="/policies", tags=["AI Policies"])


# =========================================================================
# CRUD ENDPOINTS (original — frontend uses /api/policies/*)
# =========================================================================

@router.get("", response_model=list[Policy])
def list_policies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """List all AI policies."""
    return db.query(PolicyModel).order_by(PolicyModel.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=Policy)
def create_policy(policy: PolicyCreate, db: Session = Depends(get_db)):
    """Create a new AI policy."""
    db_policy = PolicyModel(**policy.model_dump())
    db.add(db_policy)
    db.commit()
    db.refresh(db_policy)
    return db_policy


@router.get("/{policy_id}", response_model=Policy)
def get_policy(policy_id: int, db: Session = Depends(get_db)):
    """Get a specific policy by ID."""
    policy = db.query(PolicyModel).filter(PolicyModel.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.put("/{policy_id}", response_model=Policy)
def update_policy(policy_id: int, updates: PolicyUpdate, db: Session = Depends(get_db)):
    """Update an existing policy."""
    policy = db.query(PolicyModel).filter(PolicyModel.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(policy, key, value)

    policy.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(policy)
    return policy


@router.patch("/{policy_id}", response_model=Policy)
def patch_policy(policy_id: int, updates: PolicyUpdate, db: Session = Depends(get_db)):
    """Partially update an existing policy (PATCH)."""
    policy = db.query(PolicyModel).filter(PolicyModel.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    update_data = updates.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(policy, key, value)

    policy.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(policy)
    return policy


@router.delete("/{policy_id}")
def delete_policy(policy_id: int, db: Session = Depends(get_db)):
    """Delete a policy."""
    policy = db.query(PolicyModel).filter(PolicyModel.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    db.delete(policy)
    db.commit()
    return {"message": "Policy deleted", "id": policy_id}


@router.patch("/{policy_id}/toggle", response_model=Policy)
def toggle_policy(policy_id: int, db: Session = Depends(get_db)):
    """Toggle a policy between active and inactive."""
    policy = db.query(PolicyModel).filter(PolicyModel.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    policy.is_active = not policy.is_active
    policy.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(policy)
    return policy


# =========================================================================
# AI-POWERED ENDPOINTS
# =========================================================================

@router.post("/generate")
def generate_policy(req: PolicyGenerateRequest, db: Session = Depends(get_db)):
    """
    Use LLM to parse natural language into a structured policy.
    Falls back to Gemini if Nemotron is unavailable.
    """
    system_prompt = """You are an enterprise AI policy engine for a Sales Intelligence system.
Given a natural language business rule, output a JSON object with these fields:
- name: a short name for the policy
- description: a 1-sentence description
- policy_type: "logical" if it can be expressed as IF/THEN, otherwise "natural_language"
- dsl: if logical, an object with "conditions" (array of {field, operator, value}), "actions" (array of {type, value}), and "match_mode" ("all" or "any"). If natural_language, set to null.
- ai_instruction: the rule expressed as a clear instruction
- entity_name: the main entity this applies to (e.g. "lead", "contact", "opportunity")
- tags: array of relevant tag strings
- priority: integer 1-100 (1=highest)
Respond ONLY with valid JSON."""

    try:
        # Try Nemotron first, fall back to Gemini
        result = None
        try:
            result = llm.nemotron(prompt=req.prompt, system_prompt=system_prompt)
        except RuntimeError:
            log.info("Nemotron unavailable, falling back to Gemini")
            result = llm.gemini_json(f"{system_prompt}\n\nBusiness Rule: \"{req.prompt}\"")

        if isinstance(result, dict):
            return {
                "suggested_type": result.get("policy_type", "natural_language"),
                "confidence": 0.95,
                "reason": "AI parsed successfully",
                "suggested_name": result.get("name", "AI Generated Policy"),
                "summary": result.get("description", ""),
                "dsl": result.get("dsl"),
                "refined_instruction": result.get("ai_instruction", req.prompt),
                "entity_name": req.entity_name or result.get("entity_name"),
                "suggested_tags": result.get("tags", ["ai-generated"]),
            }

        return {"error": "LLM did not return valid JSON", "llm_output": result}

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        log.error(f"Policy generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/check-conflicts")
def check_conflicts(req: dict, db: Session = Depends(get_db)):
    """Check if a proposed policy conflicts with existing active policies using LLM."""
    natural_language = req.get("natural_language", "")
    policy_scope = req.get("policy_scope", "")
    entity_name = req.get("entity_name")
    
    result = policy_engine.check_conflicts(natural_language, policy_scope, entity_name, db)
    return result


class TranslateRequest(BaseModel):
    natural_language: str

@router.post("/translate")
def translate_policy(req: TranslateRequest):
    """Translate a natural language rule into structured DSL using LLM."""
    result = policy_engine.translate_to_dsl(req.natural_language)
    return result


class AnalyzeRequest(BaseModel):
    natural_language: str
    policy_type: Optional[str] = None
    entity_name: Optional[str] = None

@router.post("/analyze")
def analyze_policy(req: AnalyzeRequest):
    """Analyze a proposed rule for clarity, edge cases, and generate a refined instruction."""
    result = policy_engine.analyze_rule(req.natural_language, req.policy_type, req.entity_name)
    return result


class EvaluateRequest(BaseModel):
    data: Dict[str, Any]
    entity_name: Optional[str] = None

@router.post("/evaluate")
def evaluate_policies(req: EvaluateRequest, db: Session = Depends(get_db)):
    """
    Evaluate ALL active policies against a data payload at runtime.
    This is the core policy enforcement endpoint.
    
    Structured policies are evaluated deterministically.
    Natural language policies are evaluated via Gemini LLM.
    """
    results = policy_engine.evaluate_all_policies(req.data, db, req.entity_name)
    
    triggered = [r for r in results if r.get("applies")]
    
    return {
        "total_evaluated": len(results),
        "total_triggered": len(triggered),
        "results": results,
        "triggered_actions": [
            {"policy_id": r["policy_id"], "policy_name": r["policy_name"], "action": r["action"], "reason": r["reason"]}
            for r in triggered
        ],
    }
