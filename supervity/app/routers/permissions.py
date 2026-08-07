# app/routers/permissions.py
"""
Permission Matrix endpoints.

Persists the role -> permissions matrix (edited in the AI Policies
"Permission Matrix" tab) as JSON in the settings key-value table.
"""

import json
import logging

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session
from typing import Any

from ..core.database import get_db
from ..models.settings import Settings

log = logging.getLogger(__name__)

router = APIRouter(prefix="/permissions", tags=["Permissions"])

MATRIX_KEY = "permission_matrix"

DEFAULT_MATRIX: dict[str, list[str]] = {
    "admin": [
        "view_dashboard", "view_reports", "export_data",
        "create_policies", "edit_policies", "delete_policies",
        "view_insights", "trigger_analysis",
        "manage_users", "manage_roles", "view_audit_logs", "system_settings",
    ],
    "manager": [
        "view_dashboard", "view_reports", "export_data",
        "create_policies", "edit_policies",
        "view_insights", "trigger_analysis", "manage_users",
    ],
    "analyst": ["view_dashboard", "view_reports", "export_data", "view_insights", "trigger_analysis"],
    "operator": ["view_dashboard", "view_reports", "create_policies", "edit_policies", "view_insights"],
    "viewer": ["view_dashboard", "view_reports"],
}


class MatrixUpdate(BaseModel):
    matrix: dict[str, list[str]]


@router.get("/matrix")
def get_permission_matrix(db: Session = Depends(get_db)):
    """Return the saved permission matrix, or the default if never saved."""
    row = db.query(Settings).filter(Settings.key == MATRIX_KEY).first()
    if row and row.value:
        try:
            return {"matrix": json.loads(row.value), "is_default": False}
        except json.JSONDecodeError:
            log.warning("Stored permission matrix is corrupt; returning default")
    return {"matrix": DEFAULT_MATRIX, "is_default": True}


@router.post("/matrix")
def save_permission_matrix(update: MatrixUpdate, db: Session = Depends(get_db)):
    """Persist the permission matrix."""
    row = db.query(Settings).filter(Settings.key == MATRIX_KEY).first()
    value = json.dumps(update.matrix)
    if row:
        row.value = value
    else:
        row = Settings(key=MATRIX_KEY, value=value, description="Role -> permissions matrix from AI Policies UI")
        db.add(row)
    db.commit()
    return {"status": "saved", "matrix": update.matrix}


# General settings router (also lives here because it uses the same Settings table)
settings_router = APIRouter(prefix="/settings", tags=["Settings"])


class SettingsPayload(BaseModel):
    values: dict[str, str | int | bool]


@settings_router.get("/")
def get_settings(db: Session = Depends(get_db)):
    """Return all stored settings as a flat key/value object."""
    rows = db.query(Settings).all()
    out: dict[str, Any] = {}
    for r in rows:
        if r.value is None:
            continue
        try:
            out[r.key] = json.loads(r.value)
        except Exception:
            out[r.key] = r.value
    return out


@settings_router.put("/")
def update_settings(payload: SettingsPayload, db: Session = Depends(get_db)):
    """Upsert a batch of settings key/value pairs."""
    for key, raw in payload.values.items():
        value = json.dumps(raw) if not isinstance(raw, str) else raw
        row = db.query(Settings).filter(Settings.key == key).first()
        if row:
            row.value = value
        else:
            db.add(Settings(key=key, value=value, description=f"User setting: {key}"))
    db.commit()
    return {"status": "saved"}
