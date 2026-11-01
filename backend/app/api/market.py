"""产销对接：供应/求购 CRUD + AI 智能匹配。"""
import json
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.deps import get_current_user, get_db, require_role
from app.models import PurchaseInfo, SupplyInfo, User
from app.schemas import PurchaseCreate, StatusUpdate, SupplyCreate
from app.services.embedding import embed_text
from app.services.matcher import (
    effective_status,
    find_matches_for_purchase,
    find_matches_for_supply,
)

router = APIRouter(prefix="/api", tags=["market"])

PAGE_SIZE = 12


async def _embed_or_502(text: str) -> bytes:
    """发布/编辑时向量化，失败给出明确错误（避免无向量记录永远匹配不上）。"""
    try:
        return await embed_text(text)
    except Exception:
        raise HTTPException(502, "向量化服务暂时不可用，请稍后重试")


def _expire_at(days: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).isoformat()


def _supply_text(b: SupplyCreate) -> str:
    price = f"价格{b.price}元" if b.price is not None else "价格面议"
    return (
        f"供应{b.category} {b.variety or ''} {b.title} 数量{b.quantity}{b.unit} {price} "
        f"产地{b.region} {b.description or ''}"
    )


def _purchase_text(b: PurchaseCreate) -> str:
    return (
        f"求购{b.category} {b.title} 数量{b.quantity}{b.unit} "
        f"意向产区{b.target_region or '不限'} 预算{b.budget or '面议'} {b.description or ''}"
    )


def _supply_out(s: SupplyInfo, with_user: bool = True) -> dict:
    data = {
        "id": s.id,
        "user_id": s.user_id,
        "title": s.title,
        "category": s.category,
        "variety": s.variety,
        "quantity": s.quantity,
        "unit": s.unit,
        "price": s.price,
        "region": s.region,
        "description": s.description,
        "images": json.loads(s.images) if s.images else [],
        "status": effective_status(s),
        "expire_at": s.expire_at,
        "created_at": s.created_at,
    }
    if with_user:
        data["user_nickname"] = s.user.nickname if s.user else None
    return data


def _purchase_out(p: PurchaseInfo, with_user: bool = True) -> dict:
    data = {
        "id": p.id,
        "user_id": p.user_id,
        "title": p.title,
        "category": p.category,
        "quantity": p.quantity,
        "unit": p.unit,
        "target_region": p.target_region,
        "budget": p.budget,
        "description": p.description,
        "status": effective_status(p),
        "expire_at": p.expire_at,
        "created_at": p.created_at,
    }
    if with_user:
        data["user_nickname"] = p.user.nickname if p.user else None
    return data


# ═════════════════════════ 供应 ═════════════════════════


@router.get("/supply")
def list_supply(
    category: str | None = None,
    region: str | None = None,
    keyword: str | None = None,
    status: str | None = Query(default="active", pattern=r"^(active|offline|expired|all|mine)$"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=PAGE_SIZE, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = select(SupplyInfo)
    if status == "mine":
        q = q.where(SupplyInfo.user_id == user.id)
    else:
        q = q.where(SupplyInfo.status == status if status != "all" else SupplyInfo.status.isnot(None))
        if status == "active":  # 惰性过期：请求时过滤已过期的
            q = q.where(SupplyInfo.expire_at.is_(None) | (SupplyInfo.expire_at > datetime.now(timezone.utc).isoformat()))
    if category:
        q = q.where(SupplyInfo.category == category)
    if region:
        q = q.where(SupplyInfo.region.contains(region))
    if keyword:
        q = q.where(or_(SupplyInfo.title.contains(keyword), SupplyInfo.description.contains(keyword)))

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(
        q.order_by(SupplyInfo.created_at.desc()).offset((page - 1) * size).limit(size)
    ).all()
    # eager 加载 user，避免 N+1
    for r in rows:
        _ = r.user
    return {"list": [_supply_out(s) for s in rows], "total": total, "page": page, "size": size}


@router.post("/supply", status_code=201)
async def create_supply(
    body: SupplyCreate,
    user: User = Depends(require_role("farmer")),
    db: Session = Depends(get_db),
):
    s = SupplyInfo(
        user_id=user.id,
        title=body.title,
        category=body.category,
        variety=body.variety,
        quantity=body.quantity,
        unit=body.unit,
        price=body.price,
        region=body.region,
        description=body.description,
        images=json.dumps(body.images, ensure_ascii=False),
        expire_at=_expire_at(body.expire_days),
    )
    s.embedding = await _embed_or_502(_supply_text(body))
    db.add(s)
    db.commit()
    db.refresh(s)
    return _supply_out(s)


@router.get("/supply/{supply_id}")
def get_supply(
    supply_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.get(SupplyInfo, supply_id)
    if s is None:
        raise HTTPException(404, "供应信息不存在")
    out = _supply_out(s)
    out["user_phone"] = s.user.phone if s.user else None
    return out


@router.put("/supply/{supply_id}")
async def update_supply(
    supply_id: int,
    body: SupplyCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.get(SupplyInfo, supply_id)
    if s is None:
        raise HTTPException(404, "供应信息不存在")
    if s.user_id != user.id and user.role != "admin":
        raise HTTPException(403, "只能编辑自己发布的信息")
    for k, v in {
        "title": body.title,
        "category": body.category,
        "variety": body.variety,
        "quantity": body.quantity,
        "unit": body.unit,
        "price": body.price,
        "region": body.region,
        "description": body.description,
        "images": json.dumps(body.images, ensure_ascii=False),
        "expire_at": _expire_at(body.expire_days),
    }.items():
        setattr(s, k, v)
    s.embedding = await _embed_or_502(_supply_text(body))
    db.commit()
    return _supply_out(s)


@router.put("/supply/{supply_id}/status")
def update_supply_status(
    supply_id: int,
    body: StatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.get(SupplyInfo, supply_id)
    if s is None:
        raise HTTPException(404, "供应信息不存在")
    if s.user_id != user.id and user.role != "admin":
        raise HTTPException(403, "无权操作")
    if body.status == "closed":
        raise HTTPException(400, "供应信息不支持 closed 状态，请用 offline 下架")
    s.status = body.status
    db.commit()
    return {"id": s.id, "status": s.status}


@router.delete("/supply/{supply_id}", status_code=204)
def delete_supply(
    supply_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.get(SupplyInfo, supply_id)
    if s is None:
        raise HTTPException(404, "供应信息不存在")
    if s.user_id != user.id and user.role != "admin":
        raise HTTPException(403, "只能删除自己发布的信息")
    db.delete(s)
    db.commit()


# ═════════════════════════ 求购 ═════════════════════════


@router.get("/purchase")
def list_purchase(
    category: str | None = None,
    target_region: str | None = None,
    keyword: str | None = None,
    status: str | None = Query(default="active", pattern=r"^(active|closed|expired|all|mine)$"),
    page: int = Query(default=1, ge=1),
    size: int = Query(default=PAGE_SIZE, ge=1, le=50),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = select(PurchaseInfo)
    if status == "mine":
        q = q.where(PurchaseInfo.user_id == user.id)
    else:
        q = q.where(
            PurchaseInfo.status == status if status != "all" else PurchaseInfo.status.isnot(None)
        )
        if status == "active":
            q = q.where(
                PurchaseInfo.expire_at.is_(None)
                | (PurchaseInfo.expire_at > datetime.now(timezone.utc).isoformat())
            )
    if category:
        q = q.where(PurchaseInfo.category == category)
    if target_region:
        q = q.where(PurchaseInfo.target_region.contains(target_region))
    if keyword:
        q = q.where(or_(PurchaseInfo.title.contains(keyword), PurchaseInfo.description.contains(keyword)))

    total = db.scalar(select(func.count()).select_from(q.subquery()))
    rows = db.scalars(
        q.order_by(PurchaseInfo.created_at.desc()).offset((page - 1) * size).limit(size)
    ).all()
    for r in rows:
        _ = r.user
    return {"list": [_purchase_out(p) for p in rows], "total": total, "page": page, "size": size}


@router.post("/purchase", status_code=201)
async def create_purchase(
    body: PurchaseCreate,
    user: User = Depends(require_role("buyer")),
    db: Session = Depends(get_db),
):
    p = PurchaseInfo(
        user_id=user.id,
        title=body.title,
        category=body.category,
        quantity=body.quantity,
        unit=body.unit,
        target_region=body.target_region,
        budget=body.budget,
        description=body.description,
        expire_at=_expire_at(body.expire_days),
    )
    p.embedding = await _embed_or_502(_purchase_text(body))
    db.add(p)
    db.commit()
    db.refresh(p)
    return _purchase_out(p)


@router.get("/purchase/{purchase_id}")
def get_purchase(
    purchase_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = db.get(PurchaseInfo, purchase_id)
    if p is None:
        raise HTTPException(404, "求购信息不存在")
    out = _purchase_out(p)
    out["user_phone"] = p.user.phone if p.user else None
    return out


@router.put("/purchase/{purchase_id}")
async def update_purchase(
    purchase_id: int,
    body: PurchaseCreate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = db.get(PurchaseInfo, purchase_id)
    if p is None:
        raise HTTPException(404, "求购信息不存在")
    if p.user_id != user.id and user.role != "admin":
        raise HTTPException(403, "只能编辑自己发布的信息")
    for k, v in {
        "title": body.title,
        "category": body.category,
        "quantity": body.quantity,
        "unit": body.unit,
        "target_region": body.target_region,
        "budget": body.budget,
        "description": body.description,
        "expire_at": _expire_at(body.expire_days),
    }.items():
        setattr(p, k, v)
    p.embedding = await _embed_or_502(_purchase_text(body))
    db.commit()
    return _purchase_out(p)


@router.put("/purchase/{purchase_id}/status")
def update_purchase_status(
    purchase_id: int,
    body: StatusUpdate,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = db.get(PurchaseInfo, purchase_id)
    if p is None:
        raise HTTPException(404, "求购信息不存在")
    if p.user_id != user.id and user.role != "admin":
        raise HTTPException(403, "无权操作")
    if body.status == "offline":
        raise HTTPException(400, "求购信息不支持 offline 状态，请用 closed 关闭")
    p.status = body.status
    db.commit()
    return {"id": p.id, "status": p.status}


@router.delete("/purchase/{purchase_id}", status_code=204)
def delete_purchase(
    purchase_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = db.get(PurchaseInfo, purchase_id)
    if p is None:
        raise HTTPException(404, "求购信息不存在")
    if p.user_id != user.id and user.role != "admin":
        raise HTTPException(403, "只能删除自己发布的信息")
    db.delete(p)
    db.commit()


# ═════════════════════════ AI 匹配 ═════════════════════════


@router.get("/match/supply/{supply_id}")
async def match_for_supply(
    supply_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    s = db.get(SupplyInfo, supply_id)
    if s is None:
        raise HTTPException(404, "供应信息不存在")
    return {"matches": await find_matches_for_supply(db, s)}


@router.get("/match/purchase/{purchase_id}")
async def match_for_purchase(
    purchase_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    p = db.get(PurchaseInfo, purchase_id)
    if p is None:
        raise HTTPException(404, "求购信息不存在")
    return {"matches": await find_matches_for_purchase(db, p)}
