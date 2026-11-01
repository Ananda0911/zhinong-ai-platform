"""农技 AI 助手：SSE 流式对话（文本问答 / 病虫害图片诊断）。"""
import base64
import json
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.rate_limit import limiter
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db
from app.models import ChatMessage, ChatSession, User, now_str
from app.schemas import AgritechChatIn
from app.services.graphs.agritech import (
    AGRITECH_SYSTEM_PROMPT,
    DIAGNOSE_SYSTEM_PROMPT,
    agritech_graph,
)

router = APIRouter(prefix="/api/agritech", tags=["agritech"])

MAX_CONTEXT_ROUNDS = 10  # 保留最近 10 轮（20 条消息）


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def _load_image_as_data_url(image_url: str) -> str | None:
    """把 /uploads/... 相对路径读成 data URL（qwen-vl 需要 base64）。"""
    if not image_url:
        return None
    rel = image_url.lstrip("/").replace("uploads/", "", 1)
    path = Path("uploads") / rel
    if not path.is_file():
        return None
    mime = {"jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png", "webp": "image/webp"}.get(
        path.suffix.lstrip(".").lower(), "image/jpeg"
    )
    b64 = base64.b64encode(path.read_bytes()).decode()
    return f"data:{mime};base64,{b64}"


@router.post("/chat")
@limiter.limit("10/minute")
async def agritech_chat(
    request: Request,
    body: AgritechChatIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    session = db.get(ChatSession, body.session_id)
    if session is None or session.user_id != user.id or session.type != "agritech":
        return StreamingResponse(
            iter([_sse("error", {"message": "会话不存在"})]),
            media_type="text/event-stream",
        )

    # ── 1. 用户消息落库（首条消息生成会话标题）──
    user_msg = ChatMessage(
        session_id=session.id, role="user", content=body.content, image_url=body.image_url
    )
    db.add(user_msg)
    if not session.title:
        session.title = body.content[:20]
    db.commit()
    db.refresh(user_msg)

    # ── 2. 组装上下文：system + 最近 10 轮历史 ──
    history = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session.id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(MAX_CONTEXT_ROUNDS * 2 + 1)  # 含刚落库的本条
    ).all()
    history.reverse()

    image_data_url = _load_image_as_data_url(body.image_url or "")
    system_prompt = DIAGNOSE_SYSTEM_PROMPT if image_data_url else AGRITECH_SYSTEM_PROMPT

    messages: list = [SystemMessage(content=system_prompt)]
    for m in history:
        if m.role == "user" and m.id == user_msg.id and image_data_url:
            # 本条带图：多模态消息格式
            messages.append(
                HumanMessage(
                    content=[
                        {"type": "image_url", "image_url": {"url": image_data_url}},
                        {"type": "text", "text": body.content or "请诊断这张作物照片"},
                    ]
                )
            )
        else:
            messages.append(
                HumanMessage(content=m.content) if m.role == "user" else AIMessage(content=m.content)
            )

    graph_input = {"messages": messages, "image_data_url": image_data_url, "answer": ""}

    # ── 3. SSE 流式转发 ──
    async def event_stream():
        full = []
        try:
            async for evt in agritech_graph.astream_events(graph_input, version="v2"):
                if evt["event"] == "on_chat_model_stream":
                    delta = evt["data"]["chunk"].content
                    if delta:
                        full.append(delta)
                        yield _sse("message", {"delta": delta})
            # ── 4. AI 回复落库 ──
            answer = "".join(full)
            assistant_msg = ChatMessage(session_id=session.id, role="assistant", content=answer)
            db.add(assistant_msg)
            session.updated_at = now_str()
            db.commit()
            db.refresh(assistant_msg)
            yield _sse("done", {"message_id": assistant_msg.id})
        except Exception as e:
            db.rollback()
            yield _sse("error", {"message": "生成失败，请重试"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")
