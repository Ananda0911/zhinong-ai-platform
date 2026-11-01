"""回填：为 embedding 为空的供需记录重新计算向量（一次性别跑）。"""
import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from sqlalchemy import select

from app.database import SessionLocal
from app.models import PurchaseInfo, SupplyInfo
from app.services.embedding import embed_text


async def main():
    db = SessionLocal()
    fixed = 0

    for s in db.scalars(select(SupplyInfo).where(SupplyInfo.embedding.is_(None))).all():
        text = (
            f"供应{s.category} {s.variety or ''} {s.title} 数量{s.quantity}{s.unit} "
            f"{'价格' + str(s.price) + '元' if s.price is not None else '价格面议'} "
            f"产地{s.region} {s.description or ''}"
        )
        try:
            s.embedding = await embed_text(text)
            fixed += 1
        except Exception as e:
            print(f"supply#{s.id} FAILED: {e}")

    for p in db.scalars(select(PurchaseInfo).where(PurchaseInfo.embedding.is_(None))).all():
        text = (
            f"求购{p.category} {p.title} 数量{p.quantity}{p.unit} "
            f"意向产区{p.target_region or '不限'} 预算{p.budget or '面议'} {p.description or ''}"
        )
        try:
            p.embedding = await embed_text(text)
            fixed += 1
        except Exception as e:
            print(f"purchase#{p.id} FAILED: {e}")

    db.commit()
    print(f"backfilled {fixed} records")


asyncio.run(main())
