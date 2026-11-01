"""政策问答：SSE 流式对话（RAG 检索 Top-5 拼上下文）。"""
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from langchain_core.messages import AIMessage, HumanMessage
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import ChatMessage, ChatSession, User, now_str
from app.schemas import PolicyChatIn
from app.services.graphs.policy import policy_graph

router = APIRouter(prefix="/api/policy", tags=["policy"])

MAX_CONTEXT_ROUNDS = 10  # 保留最近 10 轮（20 条消息）


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat")
async def policy_chat(
    body: PolicyChatIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.get(ChatSession, body.session_id)
    if session is None or session.user_id != user.id or session.type != "policy":
        return StreamingResponse(
            iter([_sse("error", {"message": "会话不存在"})]),
            media_type="text/event-stream",
        )

    # ── 1. 用户消息落库（首条消息生成会话标题）──
    user_msg = ChatMessage(session_id=session.id, role="user", content=body.content)
    db.add(user_msg)
    if not session.title:
        session.title = body.content[:20]
    db.commit()
    db.refresh(user_msg)

    # ── 2. 组装历史上下文（RAG 资料 generate 节点内部拼装）──
    history = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(MAX_CONTEXT_ROUNDS * 2 + 1)
    ).all()
    history.reverse()
    messages = [
        HumanMessage(content=m.content) if m.role == "user" else AIMessage(content=m.content)
        for m in history
    ]

    graph_input = {
        "messages": messages,
        "question": body.content,
        "context": "",
        "answer": "",
    }

    # ── 3. SSE 流式转发 ──
    async def event_stream():
        full = []
        try:
            async for evt in policy_graph.astream_events(graph_input, version="v2"):
                if evt["event"] == "on_chat_model_stream":
                    delta = evt["data"]["chunk"].content
                    if delta:
                        full.append(delta)
                        yield _sse("message", {"delta": delta})
            answer = "".join(full)
            if not answer:
                raise RuntimeError("empty answer")
            assistant_msg = ChatMessage(session_id=session.id, role="assistant", content=answer)
            db.add(assistant_msg)
            session.updated_at = now_str()
            db.commit()
            db.refresh(assistant_msg)
            yield _sse("done", {"message_id": assistant_msg.id})
        except Exception:
            db.rollback()
            yield _sse("error", {"message": "生成失败，请重试"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
