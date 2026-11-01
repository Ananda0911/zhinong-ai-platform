"""Phase 3 快速验收：发布供需 → embedding → AI 匹配。"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import httpx

BASE = "http://127.0.0.1:8000/api"


async def login(client, username):
    r = await client.post(f"{BASE}/auth/login", json={"username": username, "password": "123456"})
    r.raise_for_status()
    return r.json()["access_token"]


async def main():
    async with httpx.AsyncClient(timeout=60) as c:
        farmer_token = await login(c, "farmertest")
        buyer_token = await login(c, "buyertest")
        fh = {"Authorization": f"Bearer {farmer_token}"}
        bh = {"Authorization": f"Bearer {buyer_token}"}

        # 1. farmer 发布 3 条供应
        supplies = [
            {
                "title": "洛川红富士苹果现摘批发",
                "category": "果蔬",
                "variety": "红富士",
                "quantity": 20000,
                "unit": "斤",
                "price": 3.5,
                "region": "陕西延安洛川",
                "description": "自家果园现摘红富士，果径80mm以上，糖度高，可批发可零售，量大从优，支持看货",
                "images": [],
                "expire_days": 30,
            },
            {
                "title": "散养土鸡蛋长期供应",
                "category": "畜禽",
                "variety": "土鸡蛋",
                "quantity": 500,
                "unit": "斤",
                "price": 12,
                "region": "陕西咸阳",
                "description": "散养土鸡蛋，每日新鲜产出，蛋黄金黄，长期稳定供应",
                "images": [],
                "expire_days": 60,
            },
            {
                "title": "洛川黄元帅苹果急售",
                "category": "果蔬",
                "variety": "黄元帅",
                "quantity": 8000,
                "unit": "斤",
                "price": None,
                "region": "陕西延安",
                "description": "黄元帅苹果急售，口感香甜，价格面议，欢迎采购商联系",
                "images": [],
                "expire_days": 15,
            },
        ]
        for s in supplies:
            r = await c.post(f"{BASE}/supply", json=s, headers=fh)
            r.raise_for_status()
            d = r.json()
            print(f"[supply] #{d['id']} {d['title']} status={d['status']}")

        # 2. buyer 发布 2 条求购
        purchases = [
            {
                "title": "大量收购红富士苹果",
                "category": "果蔬",
                "quantity": 30000,
                "unit": "斤",
                "target_region": "陕西",
                "budget": "3-4元/斤",
                "description": "连锁商超直采，长期大量收购陕西红富士苹果，要求果径75mm以上，口感甜脆，有稳定货源者联系",
                "expire_days": 30,
            },
            {
                "title": "求购鲜活大闸蟹",
                "category": "水产",
                "quantity": 1000,
                "unit": "斤",
                "target_region": None,
                "budget": "面议",
                "description": "中秋节前备货，求购鲜活大闸蟹，规格4两以上母蟹",
                "expire_days": 20,
            },
        ]
        for p in purchases:
            r = await c.post(f"{BASE}/purchase", json=p, headers=bh)
            r.raise_for_status()
            d = r.json()
            print(f"[purchase] #{d['id']} {d['title']} status={d['status']}")

        # 3. 匹配：供应#1(红富士) 应匹配到求购#1(收购红富士)
        r = await c.get(f"{BASE}/match/supply/1", headers=fh)
        r.raise_for_status()
        matches = r.json()["matches"]
        print("\nmatch for supply#1 (洛川红富士):")
        for m in matches:
            print(f"  {m['title']}  score={m['score']}  level={m['level']}")

        # 4. 匹配：供应#2(土鸡蛋,畜禽) 不应匹配到果蔬求购
        r = await c.get(f"{BASE}/match/supply/2", headers=fh)
        matches = r.json()["matches"]
        print(f"\nmatch for supply#2 (土鸡蛋): {len(matches)} 条（预期 0，品类硬规则）")

        # 5. 求购#1 反向匹配供应
        r = await c.get(f"{BASE}/match/purchase/1", headers=bh)
        matches = r.json()["matches"]
        print(f"\nmatch for purchase#1 (收购红富士): {len(matches)} 条")
        for m in matches:
            print(f"  {m['title']}  score={m['score']}  level={m['level']}")

        # 6. 列表筛选
        r = await c.get(f"{BASE}/supply", params={"category": "果蔬"}, headers=fh)
        d = r.json()
        print(f"\nsupply list(果蔬): total={d['total']}")
        r = await c.get(f"{BASE}/purchase", params={"keyword": "苹果"}, headers=bh)
        d = r.json()
        print(f"purchase list(关键词=苹果): total={d['total']}")


asyncio.run(main())
