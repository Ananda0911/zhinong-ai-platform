"""营销工具：文案生成（SSE 流式）+ 生成历史。"""
import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db, require_role
from app.models import MarketingRecord, User, now_str
from app.schemas import MarketingGenerateIn
from app.services.graphs.marketing import build_marketing_messages, marketing_graph

router = APIRouter(prefix="/api/marketing", tags=["marketing"])

GEN_TYPE_LABEL = {"detail": "商品文案", "live": "直播话术", "video": "短视频脚本"}


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/generate")
async def generate(
    body: MarketingGenerateIn,
    user: User = Depends(require_role("farmer")),
    db: Session = Depends(get_db),
):
    """生成营销文案：SSE 流式输出，完成后落库。"""
    messages = build_marketing_messages(
        product_name=body.product_name,
        category=body.category,
        gen_type=body.gen_type,
        features=body.features,
        selling_points=body.selling_points,
        tone=body.tone,
    )

    async def event_stream():
        full = []
        try:
            async for evt in marketing_graph.astream_events(
                {"messages": messages, "answer": ""}, version="v2"
            ):
                if evt["event"] == "on_chat_model_stream":
                    delta = evt["data"]["chunk"].content
                    if delta:
                        full.append(delta)
                        yield _sse("message", {"delta": delta})

            answer = "".join(full)
            if not answer:
                yield _sse("error", {"message": "生成结果为空，请重试"})
                return
            record = MarketingRecord(
                user_id=user.id,
                gen_type=body.gen_type,
                input_json=body.model_dump_json(),
                result=answer,
            )
            db.add(record)
            db.commit()
            db.refresh(record)
            yield _sse("done", {"record_id": record.id})
        except Exception:
            db.rollback()
            yield _sse("error", {"message": "生成失败，请稍后重试"})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/records")
def records(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """我的生成历史（最近 20 条）。"""
    rows = db.scalars(
        select(MarketingRecord)
        .where(MarketingRecord.user_id == user.id)
        .order_by(MarketingRecord.id.desc())
        .limit(20)
    ).all()
    return [
        {
            "id": r.id,
            "gen_type": r.gen_type,
            "gen_type_label": GEN_TYPE_LABEL.get(r.gen_type, r.gen_type),
            "input": json.loads(r.input_json) if r.input_json else {},
            "result": r.result,
            "created_at": r.created_at or now_str(),
        }
        for r in rows
    ]
