"""管理后台：统计看板、用户管理、内容治理、政策文档管理。

政策文档上传后立即返回 processing，FastAPI BackgroundTasks 异步执行：
解析（MinerU API / 直读）→ 分块 → 向量化入库 → ready / failed。
"""
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, UploadFile
from loguru import logger
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.deps import get_db, require_role
from app.database import SessionLocal
from app.models import (
    ChatMessage,
    ChatSession,
    MarketingRecord,
    PolicyChunk,
    PolicyDoc,
    PurchaseInfo,
    SupplyInfo,
    User,
)
from app.schemas import AdminContentStatusIn, AdminUserStatusIn
from app.services.matcher import effective_status
from app.services.mineru import ALLOWED_EXTS, MAX_FILE_SIZE, MineruError, parse_document
from app.services.rag import chunk_and_store, policy_index

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ───────────────────────── 统计看板 ─────────────────────────
@router.get("/stats")
def stats(
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    def count(model, *where):
        q = select(func.count()).select_from(model)
        if where:
            q = q.where(*where)
        return db.scalar(q) or 0

    return {
        "users": {
            "total": count(User),
            "farmer": count(User, User.role == "farmer"),
            "buyer": count(User, User.role == "buyer"),
            "admin": count(User, User.role == "admin"),
            "disabled": count(User, User.is_active == 0),  # type: ignore[arg-type]
        },
        "supply": {"total": count(SupplyInfo), "active": count(SupplyInfo, SupplyInfo.status == "active")},
        "purchase": {
            "total": count(PurchaseInfo),
            "active": count(PurchaseInfo, PurchaseInfo.status == "active"),
        },
        "chat": {
            "agritech_sessions": count(ChatSession, ChatSession.type == "agritech"),
            "policy_sessions": count(ChatSession, ChatSession.type == "policy"),
            "messages": count(ChatMessage),
        },
        "marketing": {"records": count(MarketingRecord)},
        "policy_docs": {
            "total": count(PolicyDoc),
            "ready": count(PolicyDoc, PolicyDoc.status == "ready"),
            "chunks": count(PolicyChunk),
        },
    }


# ───────────────────────── 用户管理 ─────────────────────────
@router.get("/users")
def list_users(
    keyword: str | None = None,
    role: str | None = Query(default=None, pattern=r"^(farmer|buyer|admin)$"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=50),
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    q = select(User)
    if keyword:
        kw = f"%{keyword.strip()}%"
        q = q.where(or_(User.username.like(kw), User.nickname.like(kw), User.phone.like(kw)))
    if role:
        q = q.where(User.role == role)
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(
        q.order_by(User.id.desc()).offset((page - 1) * size).limit(size)
    ).all()
    return {
        "list": [
            {
                "id": u.id,
                "username": u.username,
                "nickname": u.nickname,
                "phone": u.phone,
                "role": u.role,
                "region": u.region,
                "is_active": bool(u.is_active),
                "created_at": u.created_at,
            }
            for u in rows
        ],
        "total": total,
        "page": page,
        "size": size,
    }


@router.put("/users/{user_id}/status")
def set_user_status(
    user_id: int,
    body: AdminUserStatusIn,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """启用/禁用用户（禁用立即生效：登录 403，已发 token 每请求 401）。"""
    target = db.get(User, user_id)
    if target is None:
        raise HTTPException(404, "用户不存在")
    if target.id == user.id:
        raise HTTPException(400, "不能操作自己的账号")
    if target.role == "admin" and not body.is_active:
        raise HTTPException(400, "不能禁用管理员账号")
    target.is_active = 1 if body.is_active else 0
    db.commit()
    return {"id": target.id, "is_active": bool(target.is_active)}


# ───────────────────────── 内容治理 ─────────────────────────
def _content_out(row, typ: str) -> dict:
    nickname = row.user.nickname if row.user else None
    quantity = f"{row.quantity}{row.unit}"
    if typ == "supply":
        extra = f"{row.region} · {row.price}元/{row.unit}" if row.price else row.region
    else:
        extra = row.target_region or "不限产区"
    return {
        "id": row.id,
        "type": typ,
        "title": row.title,
        "category": row.category,
        "quantity": quantity,
        "extra": extra,
        "user_nickname": nickname,
        "status": effective_status(row),
        "raw_status": row.status,
        "created_at": row.created_at,
    }


@router.get("/contents")
def list_contents(
    type: str = Query(pattern=r"^(supply|purchase)$"),
    status: str | None = Query(default=None, pattern=r"^(active|offline|closed|expired)$"),
    keyword: str | None = None,
    page: int = Query(default=1, ge=1),
    size: int = Query(default=10, ge=1, le=50),
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    model = SupplyInfo if type == "supply" else PurchaseInfo
    q = select(model)
    if status:
        q = q.where(model.status == status)
    if keyword:
        q = q.where(model.title.like(f"%{keyword.strip()}%"))
    total = db.scalar(select(func.count()).select_from(q.subquery())) or 0
    rows = db.scalars(
        q.order_by(model.id.desc()).offset((page - 1) * size).limit(size)
    ).all()
    return {
        "list": [_content_out(r, type) for r in rows],
        "total": total,
        "page": page,
        "size": size,
    }


@router.put("/contents/{type}/{item_id}/status")
def set_content_status(
    type: str,
    item_id: int,
    body: AdminContentStatusIn,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """强制下架 / 恢复上架：supply 用 offline，purchase 用 closed。"""
    if type == "supply":
        row = db.get(SupplyInfo, item_id)
        target = {"offline": "offline", "active": "active"}.get(body.status)
    elif type == "purchase":
        row = db.get(PurchaseInfo, item_id)
        target = {"closed": "closed", "active": "active"}.get(body.status)
    else:
        raise HTTPException(400, "type 仅支持 supply / purchase")
    if row is None:
        raise HTTPException(404, "内容不存在")
    if target is None:
        raise HTTPException(400, f"不支持的状态：{body.status}")

    row.status = target
    db.commit()
    return {"id": row.id, "type": type, "status": row.status}


# ───────────────────────── 政策文档管理 ─────────────────────────
@router.post("/policy-docs")
async def upload_policy_doc(
    background: BackgroundTasks,
    file: UploadFile,
    title: str | None = None,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    """上传政策文档：立即返回 processing，后台解析 + 分块 + 向量化。"""
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTS:
        raise HTTPException(400, "仅支持 pdf / docx / txt / md 格式")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "文件不能超过 50MB")

    # 存储到 uploads/policy/yyyyMMdd_uuid.ext
    policy_dir = Path("uploads") / "policy"
    policy_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    save_name = f"{stamp}_{uuid.uuid4().hex[:8]}{ext}"
    save_path = policy_dir / save_name
    save_path.write_bytes(content)

    doc = PolicyDoc(
        title=(title or re.sub(r"\.\w+$", "", file.filename)).strip()[:100] or "未命名文档",
        file_name=file.filename,
        file_path=str(save_path).replace("\\", "/"),
        status="processing",
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    background.add_task(_process_doc, doc.id)
    return {"id": doc.id, "title": doc.title, "status": doc.status}


async def _process_doc(doc_id: int):
    """后台任务：解析 → 分块 → 向量化 → ready/failed（独立数据库会话）。"""
    with SessionLocal() as db:
        doc = db.get(PolicyDoc, doc_id)
        if doc is None:
            return
        try:
            markdown = await parse_document(Path(doc.file_path))
            doc.chunk_count = await chunk_and_store(db, doc_id, markdown)
            doc.status = "ready"
            doc.error_msg = None
            db.commit()
        except Exception as e:
            db.rollback()
            doc = db.get(PolicyDoc, doc_id)  # rollback 后重新获取
            doc.status = "failed"
            doc.chunk_count = 0
            doc.error_msg = str(e)[:200]  # 前端可见失败原因
            db.commit()
            logger.warning(f"policy-doc {doc_id} 解析失败: {e}")


@router.get("/policy-docs")
def list_policy_docs(
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    rows = db.scalars(select(PolicyDoc).order_by(PolicyDoc.id.desc())).all()
    return [
        {
            "id": r.id,
            "title": r.title,
            "file_name": r.file_name,
            "chunk_count": r.chunk_count,
            "status": r.status,
            "error_msg": r.error_msg,
            "created_at": r.created_at,
        }
        for r in rows
    ]


@router.delete("/policy-docs/{doc_id}")
def delete_policy_doc(
    doc_id: int,
    user: User = Depends(require_role("admin")),
    db: Session = Depends(get_db),
):
    doc = db.get(PolicyDoc, doc_id)
    if doc is None:
        raise HTTPException(404, "文档不存在")
    file_path = doc.file_path  # 删除前先取，commit 后对象失效
    chunk_ids = db.scalars(select(PolicyChunk.id).where(PolicyChunk.doc_id == doc_id)).all()
    db.delete(doc)  # chunks 级联删除
    db.commit()
    policy_index.remove_many(list(chunk_ids))  # 同步移除 FAISS 索引
    try:
        Path(file_path).unlink(missing_ok=True)
    except OSError:
        pass
    return {"ok": True}
