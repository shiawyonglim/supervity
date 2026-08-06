# app/routers/ai_policies.py
"""
AI Policies sub-router under /ai/policies prefix.

The frontend's PolicyEditModal, TeachAI, and RuleBuilderModal components
use endpoints at /api/ai/policies/* for CRUD, translation, and analysis.
This router mirrors the main policies router but under the /ai/policies prefix.
"""

import logging
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.policy import Policy as PolicyModel
from ..schemas.policy import Policy, PolicyCreate, PolicyUpdate
from ..services import policy_engine

log = logging.getLogger(__name__)

router = APIRouter(prefix="/ai/policies", tags=["AI Policies (AI Prefix)"])


# =========================================================================
# CRUD under /api/ai/policies
# =========================================================================

@router.get("", response_model=list[Policy])
def list_policies(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return db.query(PolicyModel).order_by(PolicyModel.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=Policy)
def create_policy(policy: PolicyCreate, db: Session = Depends(get_db)):
    db_policy = PolicyModel(**policy.model_dump())
    db.add(db_policy)
    db.commit()
    db.refresh(db_policy)
    return db_policy


@router.get("/{policy_id}", response_model=Policy)
def get_policy(policy_id: int, db: Session = Depends(get_db)):
    policy = db.query(PolicyModel).filter(PolicyModel.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    return policy


@router.patch("/{policy_id}", response_model=Policy)
def patch_policy(policy_id: int, updates: PolicyUpdate, db: Session = Depends(get_db)):
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


@router.patch("/{policy_id}/toggle", response_model=Policy)
def toggle_policy(policy_id: int, db: Session = Depends(get_db)):
    policy = db.query(PolicyModel).filter(PolicyModel.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    policy.is_active = not policy.is_active
    policy.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(policy)
    return policy


@router.delete("/{policy_id}")
def delete_policy(policy_id: int, db: Session = Depends(get_db)):
    policy = db.query(PolicyModel).filter(PolicyModel.id == policy_id).first()
    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")
    db.delete(policy)
    db.commit()
    return {"message": "Policy deleted", "id": policy_id}


# =========================================================================
# AI-POWERED ENDPOINTS under /api/ai/policies/*
# =========================================================================

class TranslateRequest(BaseModel):
    natural_language: str

@router.post("/translate")
def translate_policy(req: TranslateRequest):
    """Translate natural language rule into structured DSL."""
    result = policy_engine.translate_to_dsl(req.natural_language)
    return result


class AnalyzeRequest(BaseModel):
    natural_language: str
    policy_type: Optional[str] = None
    entity_name: Optional[str] = None

@router.post("/analyze")
def analyze_policy(req: AnalyzeRequest):
    """Analyze a proposed rule for clarity, edge cases, and suggestions."""
    result = policy_engine.analyze_rule(req.natural_language, req.policy_type, req.entity_name)
    return result
