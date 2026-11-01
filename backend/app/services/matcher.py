"""产销智能匹配：FAISS 向量检索 + 品类/状态 DB 层过滤。

设计：supply_index / purchase_index 两个进程内 FAISS 索引，
索引只管"存在性"——品类一致、active、未过期等条件在检索后
按数据库状态过滤，因此上下架/惰性过期无需同步索引，
仅发布（add）、编辑（向量重算 → remove+add）、删除（remove）时同步。
"""
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PurchaseInfo, SupplyInfo
from app.services.embedding import score_level
from app.services.vector_index import VectorIndex

TOP_K = 5
CANDIDATES = 60  # FAISS 候选量：覆盖当前量级下全量，再按元数据过滤

supply_index = VectorIndex()
purchase_index = VectorIndex()


def rebuild_market_indexes(db: Session) -> tuple[int, int]:
    """启动时从 SQLite 全量重建供需索引。返回 (供应条数, 求购条数)。"""
    sup = db.execute(
        select(SupplyInfo.id, SupplyInfo.embedding).where(SupplyInfo.embedding.isnot(None))
    ).all()
    supply_index.rebuild([(r[0], r[1]) for r in sup])
    pur = db.execute(
        select(PurchaseInfo.id, PurchaseInfo.embedding).where(PurchaseInfo.embedding.isnot(None))
    ).all()
    purchase_index.rebuild([(r[0], r[1]) for r in pur])
    return len(sup), len(pur)


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
    """为一条供应匹配求购方 Top-5（FAISS 检索 → 品类/active/未过期过滤）。"""
    if not supply.embedding:
        return []
    hits = purchase_index.search(supply.embedding, CANDIDATES)
    if not hits:
        return []
    ids = [h[0] for h in hits]
    rows = {p.id: p for p in db.scalars(select(PurchaseInfo).where(PurchaseInfo.id.in_(ids))).all()}
    out = []
    for pid, score in hits:
        p = rows.get(pid)
        if p is None or p.category != supply.category or effective_status(p) != "active":
            continue
        out.append(_match_item(p, score, "purchase"))
        if len(out) >= TOP_K:
            break
    return out


async def find_matches_for_purchase(db: Session, purchase: PurchaseInfo) -> list[dict]:
    """为一条求购匹配供应方 Top-5（对称逻辑）。"""
    if not purchase.embedding:
        return []
    hits = supply_index.search(purchase.embedding, CANDIDATES)
    if not hits:
        return []
    ids = [h[0] for h in hits]
    rows = {s.id: s for s in db.scalars(select(SupplyInfo).where(SupplyInfo.id.in_(ids))).all()}
    out = []
    for sid, score in hits:
        s = rows.get(sid)
        if s is None or s.category != purchase.category or effective_status(s) != "active":
            continue
        out.append(_match_item(s, score, "supply"))
        if len(out) >= TOP_K:
            break
    return out
