"""Phase 5 联调验收：统计看板 + 用户管理（禁用全链路）+ 内容治理 + 权限。

运行：backend/ 下 .venv\\Scripts\\python scripts\\test_phase5.py
前置：后端 8000 运行中；farmertest/buyertest/admin 存在（密码 123456）。
"""
import time

import httpx

BASE = "http://127.0.0.1:8000"


def login(client, username):
    r = client.post(f"{BASE}/api/auth/login", json={"username": username, "password": "123456"})
    r.raise_for_status()
    return r.json()["access_token"]


def main():
    client = httpx.Client(timeout=30)

    # ── 1. 统计看板 ──
    print("[1/6] 统计看板 /api/admin/stats ……")
    admin_tok = login(client, "admin")
    H = {"Authorization": f"Bearer {admin_tok}"}
    r = client.get(f"{BASE}/api/admin/stats", headers=H)
    r.raise_for_status()
    s = r.json()
    assert s["users"]["total"] >= 3, "用户统计异常"
    assert s["supply"]["total"] >= 1 and s["policy_docs"]["ready"] >= 1, "业务统计异常"
    print(f"      ok：用户 {s['users']['total']}（农户{s['users']['farmer']}/采购{s['users']['buyer']}），"
          f"供应 {s['supply']['total']}，政策分块 {s['policy_docs']['chunks']}")

    # ── 2. 用户列表（搜索 + 筛选 + 分页）──
    print("[2/6] 用户列表（搜索/筛选）……")
    r = client.get(f"{BASE}/api/admin/users", params={"keyword": "farmertest"}, headers=H)
    r.raise_for_status()
    assert r.json()["total"] == 1, "搜索结果异常"
    r = client.get(f"{BASE}/api/admin/users", params={"role": "buyer"}, headers=H)
    buyers = r.json()
    assert all(u["role"] == "buyer" for u in buyers["list"]), "角色筛选异常"
    print(f"      ok：搜索 farmertest 命中 1 条；buyer 筛选 {buyers['total']} 条")

    # ── 3. 禁用用户全链路 ──
    print("[3/6] 禁用用户全链路（登录拦截 + token 立即失效）……")
    # 3.1 注册临时用户
    uname = f"testdisable{int(time.time()) % 100000}"
    r = client.post(
        f"{BASE}/api/auth/register",
        json={"username": uname, "password": "123456", "nickname": "临时测试", "role": "farmer"},
    )
    r.raise_for_status()
    # 3.2 登录拿 token
    tok = login(client, uname)
    r = client.get(f"{BASE}/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200, "临时用户初始应可用"
    uid = r.json()["id"]
    # 3.3 admin 禁用
    r = client.put(f"{BASE}/api/admin/users/{uid}/status", json={"is_active": False}, headers=H)
    r.raise_for_status()
    # 3.4 登录被拒（403）
    r = client.post(f"{BASE}/api/auth/login", json={"username": uname, "password": "123456"})
    assert r.status_code == 403, f"禁用后登录应 403，实际 {r.status_code}"
    # 3.5 旧 token 每请求 401
    r = client.get(f"{BASE}/api/auth/me", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 401, f"禁用后旧 token 应 401，实际 {r.status_code}"
    # 3.6 不能禁用自己 / 不能禁用 admin
    me = client.get(f"{BASE}/api/auth/me", headers=H).json()
    r = client.put(f"{BASE}/api/admin/users/{me['id']}/status", json={"is_active": False}, headers=H)
    assert r.status_code == 400, "禁用自己应 400"
    admin2 = client.get(f"{BASE}/api/admin/users", params={"role": "admin"}, headers=H).json()["list"]
    other_admin = next((u for u in admin2 if u["id"] != me["id"]), None)
    if other_admin:
        r = client.put(f"{BASE}/api/admin/users/{other_admin['id']}/status", json={"is_active": False}, headers=H)
        assert r.status_code == 400, "禁用管理员应 400"
    # 3.7 恢复启用 → 登录恢复
    r = client.put(f"{BASE}/api/admin/users/{uid}/status", json={"is_active": True}, headers=H)
    r.raise_for_status()
    r = client.post(f"{BASE}/api/auth/login", json={"username": uname, "password": "123456"})
    assert r.status_code == 200, "启用后登录应恢复"
    print("      ok：禁用→登录403 + 旧token401；启用→恢复；自身/admin 保护生效")

    # ── 4. 内容治理（supply 强制下架 → 恢复）──
    print("[4/6] 内容治理（强制下架/恢复）……")
    r = client.get(f"{BASE}/api/admin/contents", params={"type": "supply", "status": "active"}, headers=H)
    r.raise_for_status()
    supply_active = r.json()["list"]
    assert supply_active, "没有在售供应可测"
    target = supply_active[0]
    r = client.put(
        f"{BASE}/api/admin/contents/supply/{target['id']}/status",
        json={"status": "offline"},
        headers=H,
    )
    r.raise_for_status()
    r = client.get(f"{BASE}/api/admin/contents", params={"type": "supply", "status": "offline"}, headers=H)
    assert any(x["id"] == target["id"] for x in r.json()["list"]), "下架后应出现在 offline 列表"
    # 恢复
    r = client.put(
        f"{BASE}/api/admin/contents/supply/{target['id']}/status",
        json={"status": "active"},
        headers=H,
    )
    r.raise_for_status()
    print(f"      ok：供应 #{target['id']} 下架→offline 列表，已恢复 active")

    # ── 5. 内容治理（purchase 关闭）──
    print("[5/6] 内容治理（求购关闭）……")
    r = client.get(f"{BASE}/api/admin/contents", params={"type": "purchase", "status": "active"}, headers=H)
    purchases = r.json()["list"]
    if purchases:
        pid = purchases[0]["id"]
        r = client.put(
            f"{BASE}/api/admin/contents/purchase/{pid}/status",
            json={"status": "closed"},
            headers=H,
        )
        r.raise_for_status()
        client.put(f"{BASE}/api/admin/contents/purchase/{pid}/status", json={"status": "active"}, headers=H)
        print(f"      ok：求购 #{pid} closed→恢复 active")
    else:
        print("      跳过：无在途求购")

    # ── 6. 角色权限 ──
    print("[6/6] 角色权限（farmer/buyer 访问 admin 接口应 403）……")
    for role in ("farmertest", "buyertest"):
        tok_r = login(client, role)
        for path in ("/api/admin/stats", "/api/admin/users", "/api/admin/contents?type=supply"):
            r = client.get(f"{BASE}{path}", headers={"Authorization": f"Bearer {tok_r}"})
            assert r.status_code == 403, f"{role} 访问 {path} 应 403，实际 {r.status_code}"
    print("      ok：farmer/buyer 访问全部 admin 接口 403")

    print("\nPhase 5 验收全部通过 ✔")


if __name__ == "__main__":
    main()
