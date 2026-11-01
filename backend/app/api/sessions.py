"""会话管理（农技/政策共用）。"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import ChatMessage, ChatSession, User
from app.schemas import MessageOut, SessionCreate, SessionOut

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def _get_own_session(session_id: int, user: User, db: Session) -> ChatSession:
    s = db.get(ChatSession, session_id)
    if s is None or s.user_id != user.id:
        raise HTTPException(404, "会话不存在")
    return s


@router.get("", response_model=list[SessionOut])
def list_sessions(
    type: str = Query(pattern=r"^(agritech|policy)$"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    sessions = db.scalars(
        select(ChatSession)
        .where(ChatSession.user_id == user.id, ChatSession.type == type)
        .order_by(ChatSession.updated_at.desc())
    ).all()
    return sessions


@router.post("", response_model=SessionOut, status_code=201)
def create_session(
    body: SessionCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = ChatSession(user_id=user.id, type=body.type)
    db.add(s)
    db.commit()
    db.refresh(s)
    return s


@router.get("/{session_id}/messages", response_model=list[MessageOut])
def list_messages(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _get_own_session(session_id, user, db)
    return db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
    ).all()


@router.delete("/{session_id}", status_code=204)
def delete_session(
    session_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = _get_own_session(session_id, user, db)
    db.delete(s)  # 级联删消息（models 中 cascade）
    db.commit()
