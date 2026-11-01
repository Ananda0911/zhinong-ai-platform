"""产销智能匹配：品类硬规则过滤 + embedding 余弦相似度 Top-5。"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PurchaseInfo, SupplyInfo
from app.services.embedding import cosine_sim, score_level

TOP_K = 5


def effective_status(row) -> str:
    """惰性过期判断：active 但已过 expire_at → expired（不写库，读时判断）。"""
    if row.status != "active":
        return row.status
    if row.expire_at:
        try:
            if datetime.fromisoformat(row.expire_at) < datetime.now(timezone.utc):
                return "expired"
        except ValueError:
            pass
    return "active"


def _match_item(row, score: float, kind: str) -> dict:
    return {
        "id": row.id,
        "type": kind,
        "title": row.title,
        "category": row.category,
        "region": getattr(row, "region", None) or getattr(row, "target_region", None),
        "quantity": row.quantity,
        "unit": row.unit,
        "price": getattr(row, "price", None),
        "score": round(score, 4),
        "level": score_level(score),
        "status": effective_status(row),
    }


async def find_matches_for_supply(db: Session, supply: SupplyInfo) -> list[dict]:
    """为一条供应匹配求购方 Top-5（品类一致 + active + 未过期）。"""
    if not supply.embedding:
        return []
    rows = db.scalars(select(PurchaseInfo).where(PurchaseInfo.category == supply.category)).all()
    scored = []
    for p in rows:
        if effective_status(p) != "active":
            continue
        s = cosine_sim(supply.embedding, p.embedding)
        scored.append(_match_item(p, s, "purchase"))
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:TOP_K]


async def find_matches_for_purchase(db: Session, purchase: PurchaseInfo) -> list[dict]:
    """为一条求购匹配供应方 Top-5。"""
    if not purchase.embedding:
        return []
    rows = db.scalars(select(SupplyInfo).where(SupplyInfo.category == purchase.category)).all()
    scored = []
    for s in rows:
        if effective_status(s) != "active":
            continue
        sc = cosine_sim(purchase.embedding, s.embedding)
        scored.append(_match_item(s, sc, "supply"))
    scored.sort(key=lambda x: x["score"], reverse=True)
    return scored[:TOP_K]
