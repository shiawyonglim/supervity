# app/routers/exceptions.py
"""Workbench exception endpoints — human-in-the-loop queue."""

import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..core.database import get_db
from ..models.exception import Exception as ExceptionModel
from ..schemas.exception import ExceptionCreate, ExceptionRead, ExceptionResolve

log = logging.getLogger(__name__)

router = APIRouter(prefix="/exceptions", tags=["Workbench"])


@router.get("", response_model=list[ExceptionRead])
def list_exceptions(
    status: str = None,
    severity: str = None,
    skip: int = 0,
    limit: int = 50,
    db: Session = Depends(get_db),
):
    """List exceptions in the Workbench queue, optionally filtered by status or severity."""
    query = db.query(ExceptionModel)
    if status:
        query = query.filter(ExceptionModel.status == status)
    if severity:
        query = query.filter(ExceptionModel.severity == severity)
    return query.order_by(ExceptionModel.created_at.desc()).offset(skip).limit(limit).all()


@router.post("", response_model=ExceptionRead)
def create_exception(exc: ExceptionCreate, db: Session = Depends(get_db)):
    """Create a new exception (typically called by the orchestrator when AI can't decide)."""
    db_exc = ExceptionModel(**exc.model_dump())
    db.add(db_exc)
    db.commit()
    db.refresh(db_exc)
    return db_exc


@router.get("/stats")
def exception_stats(db: Session = Depends(get_db)):
    """Get exception counts grouped by status and severity."""
    all_exceptions = db.query(ExceptionModel).all()

    by_status = {}
    by_severity = {}
    for exc in all_exceptions:
        by_status[exc.status] = by_status.get(exc.status, 0) + 1
        by_severity[exc.severity] = by_severity.get(exc.severity, 0) + 1

    return {
        "total": len(all_exceptions),
        "by_status": by_status,
        "by_severity": by_severity,
    }


@router.get("/{exception_id}", response_model=ExceptionRead)
def get_exception(exception_id: int, db: Session = Depends(get_db)):
    """Get a specific exception with full context."""
    exc = db.query(ExceptionModel).filter(ExceptionModel.id == exception_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")
    return exc


@router.patch("/{exception_id}/resolve", response_model=ExceptionRead)
def resolve_exception(exception_id: int, resolution: ExceptionResolve, db: Session = Depends(get_db)):
    """Resolve an exception — human approves, rejects, or modifies."""
    exc = db.query(ExceptionModel).filter(ExceptionModel.id == exception_id).first()
    if not exc:
        raise HTTPException(status_code=404, detail="Exception not found")

    exc.status = "resolved"
    exc.resolution_action = resolution.resolution_action
    exc.resolved_by = resolution.resolved_by
    exc.resolution_notes = resolution.resolution_notes
    exc.resolved_at = datetime.utcnow()

    db.commit()
    db.refresh(exc)
    return exc
