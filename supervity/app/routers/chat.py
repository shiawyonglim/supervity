# app/routers/chat.py
"""Persist AI Manager chat sessions and let CROs review sales-team conversations."""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session, joinedload

from ..core.database import get_db
from ..models.chat_session import ChatSession, ChatSessionMessage

log = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["Chat Sessions"])


class ChatMessageInput(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None
    tool_calls: Optional[list] = None


class ChatSessionCreate(BaseModel):
    role: str
    name: str
    messages: list[ChatMessageInput]


class ChatSessionAppend(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None
    tool_calls: Optional[list] = None


@router.get("/sessions")
def list_sessions(role: Optional[str] = None, limit: int = 50, db: Session = Depends(get_db)):
    """List chat sessions, optionally filtered by role. CROs can omit the filter to see all."""
    q = db.query(ChatSession)
    if role:
        q = q.filter(ChatSession.role == role)
    q = q.order_by(ChatSession.updated_at.desc()).limit(limit)
    rows = q.all()
    return {
        "sessions": [
            {
                "id": r.id,
                "role": r.role,
                "name": r.name,
                "updated_at": r.updated_at.isoformat() if r.updated_at else None,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows
        ]
    }


@router.get("/sessions/{session_id}")
def get_session(session_id: int, db: Session = Depends(get_db)):
    """Get a single chat session with all messages."""
    session = (
        db.query(ChatSession)
        .options(joinedload(ChatSession.messages))
        .filter(ChatSession.id == session_id)
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return {
        "id": session.id,
        "role": session.role,
        "name": session.name,
        "created_at": session.created_at.isoformat() if session.created_at else None,
        "updated_at": session.updated_at.isoformat() if session.updated_at else None,
        "messages": [
            {
                "id": m.id,
                "role": m.role,
                "content": m.content,
                "timestamp": m.created_at.isoformat() if m.created_at else None,
                "tool_calls": m.tool_calls,
            }
            for m in session.messages
        ],
    }


@router.post("/sessions")
def create_session(req: ChatSessionCreate, db: Session = Depends(get_db)):
    """Create a new chat session. If a recent open session for this role exists, append instead."""
    recent = (
        db.query(ChatSession)
        .filter(ChatSession.role == req.role)
        .order_by(ChatSession.updated_at.desc())
        .first()
    )

    # Keep sessions scoped: create a new one if the last is older than 30 minutes or not present.
    if recent:
        updated = recent.updated_at or datetime.utcnow()
        if (datetime.utcnow() - updated).total_seconds() < 1800:
            for m in req.messages:
                db.add(ChatSessionMessage(
                    session_id=recent.id,
                    role=m.role,
                    content=m.content,
                    tool_calls=m.tool_calls or [],
                ))
            recent.updated_at = datetime.utcnow()
            recent.name = req.name
            db.commit()
            return get_session(recent.id, db)

    session = ChatSession(role=req.role, name=req.name)
    db.add(session)
    db.flush()
    for m in req.messages:
        db.add(ChatSessionMessage(
            session_id=session.id,
            role=m.role,
            content=m.content,
            tool_calls=m.tool_calls or [],
        ))
    db.commit()
    return get_session(session.id, db)


@router.post("/sessions/{session_id}/message")
def add_message(session_id: int, req: ChatSessionAppend, db: Session = Depends(get_db)):
    """Add a message to an existing session (used by CROs to drop recommendations)."""
    session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.add(ChatSessionMessage(
        session_id=session.id,
        role=req.role,
        content=req.content,
        tool_calls=req.tool_calls or [],
    ))
    session.updated_at = datetime.utcnow()
    db.commit()
    return get_session(session.id, db)
