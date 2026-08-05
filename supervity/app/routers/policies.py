# app/routers/policies.py
"""AI Policies CRUD endpoints — business rules that constrain the AI agents."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.policy import Policy as PolicyModel
from ..schemas.policy import Policy, PolicyCreate, PolicyGenerateRequest, PolicyUpdate
from ..services.llm_service import llm

log = logging.getLogger(__name__)

router = APIRouter(prefix="/policies", tags=["AI Policies"])


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


@router.post("/generate")
def generate_policy(req: PolicyGenerateRequest, db: Session = Depends(get_db)):
    """
    Use Nemotron 550B to parse natural language into a structured policy.
    The LLM translates the human text into IF/THEN rules.
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
        result = llm.nemotron(prompt=req.prompt, system_prompt=system_prompt)

        # If result is already a dict (parsed JSON), use it directly
        if isinstance(result, dict):
            # Create and save the policy
            policy_data = {
                "name": result.get("name", "AI Generated Policy"),
                "description": result.get("description", ""),
                "natural_language": req.prompt,
                "summary": result.get("description", ""),
                "policy_type": result.get("policy_type", "natural_language"),
                "dsl": result.get("dsl"),
                "ai_instruction": result.get("ai_instruction", req.prompt),
                "entity_name": req.entity_name or result.get("entity_name"),
                "tags": result.get("tags", ["ai-generated"]),
                "priority": result.get("priority", 50),
                "is_active": True,
            }

            db_policy = PolicyModel(**policy_data)
            db.add(db_policy)
            db.commit()
            db.refresh(db_policy)

            return {"policy": db_policy, "llm_output": result}

        # If it's a string, return as-is for debugging
        return {"llm_output": result, "error": "LLM did not return valid JSON"}

    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
    except Exception as e:
        log.error(f"Policy generation error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
