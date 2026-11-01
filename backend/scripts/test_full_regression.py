"""助农 AI 平台 · 第二轮全量回归测试（Phase 1-5 全模块 + 不同使用方式覆盖）。

运行：backend/ 下 .venv\\Scripts\\python scripts\\test_full_regression.py
前置：后端 8000 运行中；farmertest/buyertest/admin 存在（密码 123456）。
输出：控制台摘要 + data/regression_result2.json（供测试报告使用）。

第二轮扩充：流式性 delta 计数断言、供应编辑/详情、双向匹配（求购→供应）、
边界值（404/空字段/无效枚举）、三角色权限矩阵（buyer 发供应、admin 用农技）、
管理端 role 筛选/分页/自我保护/关键词搜索/政策文档列表。
"""
import json
import time
import uuid
from datetime import date
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"
TODAY = date.today().isoformat()

RESULTS = []  # {module, name, status(pass/fail), detail}


def check(module, name, cond, detail=""):
    RESULTS.append(
        {
            "module": module,
            "name": name,
            "status": "pass" if cond else "fail",
            "detail": str(detail)[:300],
        }
    )
    mark = "✔" if cond else "✘"
    print(f"  {mark} {name}" + (f"  —— {detail}" if (detail and not cond) else ""))
    return cond


def login(client, username, password="123456"):
    r = client.post(f"{BASE}/api/auth/login", json={"username": username, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def sse_post(client, url, token, payload, timeout=180):
    """POST SSE → (拼接文本, done事件, error消息, delta块数)。"""
    text, done, error, deltas = "", {}, "", 0
    with client.stream(
        "POST", url, json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=timeout
    ) as resp:
        if resp.status_code != 200:
            return "", {}, f"HTTP {resp.status_code}", 0
        event = "message"
        for line in resp.iter_lines():
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1].strip())
                if event == "message":
                    text += data["delta"]
                    deltas += 1
                elif event == "done":
                    done = data
                elif event == "error":
                    error = data["message"]
    return text, done, error, deltas


def preclean():
    """清理上次回归测试中途崩溃可能残留的数据（regr* 用户及其供应/会话/营销记录）。"""
    try:
        import sqlite3

        conn = sqlite3.connect("data/app.db")
        c = conn.cursor()
        uids = [u[0] for u in c.execute("SELECT id FROM users WHERE username LIKE 'regr%'").fetchall()]
        if uids:
            ph = ",".join("?" * len(uids))
            c.execute(
                f"DELETE FROM chat_messages WHERE session_id IN (SELECT id FROM chat_sessions WHERE user_id IN ({ph}))",
                uids,
            )
            c.execute(f"DELETE FROM chat_sessions WHERE user_id IN ({ph})", uids)
            c.execute(f"DELETE FROM marketing_records WHERE user_id IN ({ph})", uids)
            c.execute("DELETE FROM supply_infos WHERE title LIKE '%回归测试%'", ())
            c.execute("DELETE FROM purchase_infos WHERE title LIKE '%回归测试%'", ())
            c.execute(f"DELETE FROM users WHERE id IN ({ph})", uids)
            conn.commit()
        conn.close()
    except Exception as e:  # 数据库被占用等情况不阻断测试
        print(f"[preclean] 跳过：{e}")


def main():
    client = httpx.Client(timeout=60)
    t_all = time.time()
    preclean()

    # ══════════ 1. 环境与服务 ══════════
    print("\n[1] 环境与服务")
    r = client.get(f"{BASE}/api/health")
    check("环境", "健康检查 /api/health", r.status_code == 200 and r.json()["status"] == "ok")

    # ══════════ 2. 认证与账号（Phase 1）══════════
    print("\n[2] 认证与账号")
    uname = f"regr{int(time.time()) % 1000000}"
    r = client.post(
        f"{BASE}/api/auth/register",
        json={"username": uname, "password": "123456", "nickname": "回归测试员", "role": "farmer"},
    )
    check("认证", "注册新用户（farmer 角色）", r.status_code == 201, r.text)

    regr_tok = login(client, uname)
    r = client.get(f"{BASE}/api/auth/me", headers={"Authorization": f"Bearer {regr_tok}"})
    me = r.json()
    check("认证", "登录 + /auth/me 身份回显", r.status_code == 200 and me["username"] == uname
          and me["role"] == "farmer")

    # 第二种注册方式：buyer 角色
    uname_b = f"regrb{int(time.time()) % 1000000}"
    r = client.post(
        f"{BASE}/api/auth/register",
        json={"username": uname_b, "password": "123456", "nickname": "回归采购员", "role": "buyer"},
    )
    check("认证", "注册新用户（buyer 角色，第二种角色）", r.status_code == 201, r.text)

    r = client.post(f"{BASE}/api/auth/register",
                    json={"username": uname, "password": "123456", "nickname": "x", "role": "farmer"})
    check("认证", "重复用户名注册被拒（400）", r.status_code == 400, r.text)

    r = client.post(f"{BASE}/api/auth/login", json={"username": uname, "password": "wrong"})
    check("认证", "错误密码登录被拒（401）", r.status_code == 401)

    r = client.post(f"{BASE}/api/auth/login", json={"username": "nosuchuser999", "password": "123456"})
    check("认证", "不存在的用户名登录被拒（401，统一文案防枚举）", r.status_code == 401)

    r = client.post(f"{BASE}/api/auth/register",
                    json={"username": f"e{uname}", "nickname": "x", "role": "farmer"})  # 缺 password
    check("认证", "缺必填字段注册被拒（422）", r.status_code == 422, r.text)

    r = client.post(f"{BASE}/api/auth/register",
                    json={"username": f"x{uname}", "password": "123456", "nickname": "x", "role": "admin"})
    check("认证", "admin 角色注册被拒（422，不开放注册）", r.status_code == 422, r.text)

    r = client.get(f"{BASE}/api/sessions")
    check("认证", "未带 token 访问受保护接口（401）", r.status_code == 401)

    # ══════════ 3. 会话管理 ══════════
    print("\n[3] 会话管理")
    r = client.post(f"{BASE}/api/sessions", json={"type": "agritech"},
                    headers={"Authorization": f"Bearer {regr_tok}"})
    s_agri = r.json()
    check("会话", "创建农技会话", r.status_code == 201 and s_agri["type"] == "agritech", r.text)
    r = client.get(f"{BASE}/api/sessions?type=agritech", headers={"Authorization": f"Bearer {regr_tok}"})
    check("会话", "会话列表（按 type 过滤）",
          r.status_code == 200 and any(s["id"] == s_agri["id"] for s in r.json()))

    # ══════════ 4. 农技 AI 助手（Phase 2）══════════
    print("\n[4] 农技 AI 助手")
    text, done, err, deltas = sse_post(
        client, f"{BASE}/api/agritech/chat", regr_tok,
        {"session_id": s_agri["id"], "content": "番茄叶子发黄是什么原因？怎么防治？"},
    )
    check("农技AI", "文本问答（SSE 流式）", not err and len(text) > 100 and done.get("message_id"),
          err or f"{len(text)}字")
    check("农技AI", "流式性（SSE delta 分片 ≥10，验证逐字输出）", deltas >= 10, f"delta={deltas}")

    r = client.get(f"{BASE}/api/sessions/{s_agri['id']}/messages", headers={"Authorization": f"Bearer {regr_tok}"})
    msgs = r.json()
    check("农技AI", "问答消息落库（user+assistant 成对）",
          r.status_code == 200 and len(msgs) >= 2 and msgs[-1]["role"] == "assistant",
          f"{len(msgs)}条消息")
    r = client.get(f"{BASE}/api/sessions?type=agritech", headers={"Authorization": f"Bearer {regr_tok}"})
    titled = next((s for s in r.json() if s["id"] == s_agri["id"]), {})
    check("农技AI", "会话标题=首条消息前20字", titled.get("title") == "番茄叶子发黄是什么原因？怎么防治？"[:20])

    # 多轮上下文：第二问依赖第一轮语境
    text_c, _, err_c, _ = sse_post(
        client, f"{BASE}/api/agritech/chat", regr_tok,
        {"session_id": s_agri["id"], "content": "那平时预防要注意什么？"},
    )
    check("农技AI", "多轮上下文（追问「那平时预防」）", not err_c and len(text_c) > 60,
          err_c or f"{len(text_c)}字")

    # 图片诊断：Pillow 造一张"病斑叶"图（多模态使用方式）
    try:
        from PIL import Image, ImageDraw
        img = Image.new("RGB", (512, 512), (240, 248, 240))
        d = ImageDraw.Draw(img)
        d.ellipse((80, 120, 430, 430), fill=(76, 153, 82))  # 叶片
        for cx, cy, rr in [(180, 220, 26), (280, 300, 34), (350, 200, 20)]:  # 病斑
            d.ellipse((cx - rr, cy - rr, cx + rr, cy + rr), fill=(194, 160, 62))
        p = Path("data/_reg_leaf.jpg")
        img.save(p, "JPEG", quality=88)
        with open(p, "rb") as f:
            r = client.post(f"{BASE}/api/upload/image", files={"file": ("leaf.jpg", f, "image/jpeg")},
                            headers={"Authorization": f"Bearer {regr_tok}"})
        img_url = r.json().get("url")
        check("农技AI", "图片上传（≤2MB jpg）", r.status_code == 200 and img_url, r.text)
        text2, done2, err2, deltas2 = sse_post(
            client, f"{BASE}/api/agritech/chat", regr_tok,
            {"session_id": s_agri["id"], "content": "帮我看看这片叶子怎么了", "image_url": img_url},
        )
        check("农技AI", "拍照诊断（多模态 qwen3-vl-plus）", not err2 and len(text2) > 100,
              err2 or f"{len(text2)}字")
        check("农技AI", "多模态回答同样流式（delta≥10）", deltas2 >= 10, f"delta={deltas2}")
        p.unlink(missing_ok=True)
    except ImportError:
        check("农技AI", "拍照诊断（多模态）", False, "Pillow 未安装，跳过")

    # ══════════ 5. 产销对接（Phase 3）══════════
    print("\n[5] 产销对接")
    stamp = uuid.uuid4().hex[:6]
    buyer_tok = login(client, "buyertest")
    HB = {"Authorization": f"Bearer {buyer_tok}"}

    sup_payload = {
        "title": f"回归测试红富士苹果{stamp}", "category": "果蔬", "region": "陕西延安",
        "quantity": 5000, "unit": "斤", "price": 4.5, "expire_days": 30,
        "description": "洛川红富士，脆甜多汁，回归测试数据",
    }
    r = client.post(f"{BASE}/api/supply", headers={"Authorization": f"Bearer {regr_tok}"}, json=sup_payload)
    sup = r.json()
    check("产销", "发布供应（含向量化）", r.status_code == 201 and sup.get("id"), r.text)

    # 供应详情
    r = client.get(f"{BASE}/api/supply/{sup['id']}", headers={"Authorization": f"Bearer {regr_tok}"})
    check("产销", "供应详情（DetailView 数据源）",
          r.status_code == 200 and r.json()["title"].startswith("回归测试"), r.text)

    # 编辑供应（第二种操作方式）
    edited = dict(sup_payload, price=5.8, description="编辑后：现摘现发，回归测试数据")
    r = client.put(f"{BASE}/api/supply/{sup['id']}", headers={"Authorization": f"Bearer {regr_tok}"}, json=edited)
    r2 = client.get(f"{BASE}/api/supply/{sup['id']}", headers={"Authorization": f"Bearer {regr_tok}"})
    check("产销", "编辑供应（改价格改描述）",
          r.status_code == 200 and r2.json().get("price") == 5.8, r.text)

    pur_payload = {
        "title": f"求购红富士苹果{stamp}", "category": "果蔬", "quantity": 3000, "unit": "斤",
        "target_region": "陕西", "budget": "5元/斤", "expire_days": 30,
        "description": "长期求购延安红富士，回归测试数据",
    }
    r = client.post(f"{BASE}/api/purchase", headers=HB, json=pur_payload)
    pur = r.json()
    check("产销", "发布求购（buyer 角色）", r.status_code == 201 and pur.get("id"), r.text)

    r = client.get(f"{BASE}/api/supply", params={"category": "果蔬", "keyword": stamp},
                   headers={"Authorization": f"Bearer {regr_tok}"})
    check("产销", "供应列表（品类+关键词筛选）", any(x["id"] == sup["id"] for x in r.json()["list"]))

    # 双向匹配：供应→求购
    r = client.get(f"{BASE}/api/match/supply/{sup['id']}", headers={"Authorization": f"Bearer {regr_tok}"})
    matches = r.json()["matches"]
    hit = next((m for m in matches if m["id"] == pur["id"]), None)
    check("产销", "AI 向量匹配（供应→求购 Top-5 命中）", hit is not None and hit["score"] > 0.5,
          f"score={hit['score']:.3f}" if hit else "未命中")

    # 双向匹配：求购→供应
    r = client.get(f"{BASE}/api/match/purchase/{pur['id']}", headers=HB)
    matches2 = r.json()["matches"]
    hit2 = next((m for m in matches2 if m["id"] == sup["id"]), None)
    check("产销", "AI 向量匹配（求购→供应 反向命中）", hit2 is not None and hit2["score"] > 0.5,
          f"score={hit2['score']:.3f}" if hit2 else "未命中")

    # 求购关闭（closed 状态流转）
    r = client.put(f"{BASE}/api/purchase/{pur['id']}/status", json={"status": "closed"}, headers=HB)
    r = client.get(f"{BASE}/api/purchase", params={"status": "mine"}, headers=HB)
    mine_p = next((x for x in r.json()["list"] if x["id"] == pur["id"]), {})
    check("产销", "求购关闭（closed 状态流转）", mine_p.get("status") == "closed")

    r = client.put(f"{BASE}/api/supply/{sup['id']}/status", json={"status": "offline"},
                   headers={"Authorization": f"Bearer {regr_tok}"})
    r = client.get(f"{BASE}/api/supply", params={"status": "mine"}, headers={"Authorization": f"Bearer {regr_tok}"})
    mine = next((x for x in r.json()["list"] if x["id"] == sup["id"]), {})
    check("产销", "供应下架（offline 状态流转）", mine.get("status") == "offline")

    # 权限：buyer 不能发布供应
    r = client.post(f"{BASE}/api/supply", headers=HB, json=dict(sup_payload, title=f"越权{stamp}"))
    check("产销", "权限矩阵（buyer 发布供应被拒 403）", r.status_code == 403, f"HTTP {r.status_code}")

    # 边界：不存在的资源
    r = client.get(f"{BASE}/api/supply/999999", headers={"Authorization": f"Bearer {regr_tok}"})
    check("产销", "边界（查询不存在供应 404）", r.status_code == 404, f"HTTP {r.status_code}")

    r = client.delete(f"{BASE}/api/supply/{sup['id']}", headers={"Authorization": f"Bearer {regr_tok}"})
    client.delete(f"{BASE}/api/purchase/{pur['id']}", headers=HB)
    check("产销", "清理测试供需（删除 204）", r.status_code == 204, r.text)

    # ══════════ 6. 营销工具（Phase 4a）══════════
    print("\n[6] 营销工具")
    farmer_tok = login(client, "farmertest")
    HF = {"Authorization": f"Bearer {farmer_tok}"}
    gen_cases = [
        ("detail", "商品文案", ["标题", "卖点"]),
        ("live", "直播话术", ["开场", "促单"]),
        ("video", "短视频脚本", ["镜号", "口播"]),
    ]
    for gtype, label, kws in gen_cases:
        text, done, err, _ = sse_post(
            client, f"{BASE}/api/marketing/generate", farmer_tok,
            {"product_name": "洛川红富士苹果", "category": "果蔬", "features": "高原种植，昼夜温差大",
             "gen_type": gtype, "tone": "接地气"},
        )
        ok = not err and len(text) > 150 and any(k in text for k in kws)
        check("营销", f"{label}生成（gen_type={gtype}，SSE）", ok, err or f"{len(text)}字")

    # 无效 gen_type
    r = client.post(f"{BASE}/api/marketing/generate",
                    headers={**HF, "Accept": "text/event-stream"},
                    json={"product_name": "x", "category": "果蔬", "features": "x",
                          "gen_type": "invalid", "tone": "x"})
    check("营销", "边界（无效 gen_type 被拒 422）", r.status_code == 422, f"HTTP {r.status_code}")

    # 权限：buyer 不能用营销工具
    r = client.post(f"{BASE}/api/marketing/generate", headers={**HB, "Accept": "text/event-stream"},
                    json={"product_name": "x", "category": "果蔬", "features": "x",
                          "gen_type": "detail", "tone": "x"})
    check("营销", "权限矩阵（buyer 调用营销生成 403）", r.status_code == 403, f"HTTP {r.status_code}")

    r = client.get(f"{BASE}/api/marketing/records", headers=HF)
    check("营销", "生成历史（最近20条）", r.status_code == 200 and len(r.json()) >= 3)

    # ══════════ 7. 政策问答 RAG（Phase 4b）══════════
    print("\n[7] 政策问答（RAG）")
    r = client.post(f"{BASE}/api/sessions", json={"type": "policy"}, headers=HF)
    s_pol = r.json()
    text, _, err, deltas_p = sse_post(
        client, f"{BASE}/api/policy/chat", farmer_tok,
        {"session_id": s_pol["id"], "content": "种粮农民一次性补贴每亩多少钱？"},
    )
    check("政策RAG", "知识库命中（引用文档金额 120 元）", not err and "120" in text, err or text[:80])
    check("政策RAG", "流式性（RAG 回答 delta≥5）", deltas_p >= 5, f"delta={deltas_p}")

    text, _, err, _ = sse_post(
        client, f"{BASE}/api/policy/chat", farmer_tok,
        {"session_id": s_pol["id"], "content": "农村宅基地翻建审批流程是什么？"},
    )
    check("政策RAG", "知识库外拒答（不编造）", not err and "暂无" in text, err or text[:80])

    r = client.get(f"{BASE}/api/sessions/{s_pol['id']}/messages", headers=HF)
    check("政策RAG", "多轮上下文消息落库", len(r.json()) >= 4)

    r = client.get(f"{BASE}/api/sessions?type=policy", headers=HF)
    check("政策RAG", "会话列表（type=policy 过滤）",
          any(s["id"] == s_pol["id"] for s in r.json()))

    # ══════════ 8. 管理后台（Phase 5）══════════
    print("\n[8] 管理后台")
    admin_tok = login(client, "admin")
    HA = {"Authorization": f"Bearer {admin_tok}"}

    r = client.get(f"{BASE}/api/admin/stats", headers=HA)
    s = r.json()
    stats_ok = (s["users"]["total"] >= 4 and s["supply"]["total"] >= 3
                and s["policy_docs"]["ready"] >= 3 and s["policy_docs"]["chunks"] >= 3)
    check("管理", "统计看板（数据一致性）", stats_ok,
          f"用户{s['users']['total']}/供应{s['supply']['total']}/文档{s['policy_docs']['ready']}")

    # 用户搜索 + role 筛选 + 分页（三种查询方式）
    r = client.get(f"{BASE}/api/admin/users", params={"keyword": uname}, headers=HA)
    regr_user = next((u for u in r.json()["list"] if u["username"] == uname), None)
    check("管理", "用户搜索（keyword 命中）", regr_user is not None)

    r = client.get(f"{BASE}/api/admin/users", params={"role": "buyer"}, headers=HA)
    roles_ok = r.json()["total"] >= 2 and all(u["role"] == "buyer" for u in r.json()["list"])
    check("管理", "用户列表（role=buyer 筛选）", roles_ok,
          f"total={r.json()['total']}")

    r = client.get(f"{BASE}/api/admin/users", params={"page": 1, "size": 2}, headers=HA)
    page_ok = len(r.json()["list"]) <= 2 and r.json()["size"] == 2 and r.json()["total"] > 2
    check("管理", "用户列表（分页 size=2）", page_ok, f"返回{len(r.json()['list'])}条/共{r.json()['total']}")

    # 禁用链路
    r = client.put(f"{BASE}/api/admin/users/{regr_user['id']}/status", json={"is_active": False}, headers=HA)
    r = client.post(f"{BASE}/api/auth/login", json={"username": uname, "password": "123456"})
    dis_login = r.status_code == 403
    r = client.get(f"{BASE}/api/auth/me", headers={"Authorization": f"Bearer {regr_tok}"})
    dis_token = r.status_code == 401
    check("管理", "禁用用户（登录403 + 旧token立即401）", dis_login and dis_token,
          f"login={dis_login}, token={dis_token}")
    client.put(f"{BASE}/api/admin/users/{regr_user['id']}/status", json={"is_active": True}, headers=HA)

    # 自我保护：不能禁自己 / 不能禁 admin
    admin_me = client.get(f"{BASE}/api/auth/me", headers=HA).json()
    r = client.put(f"{BASE}/api/admin/users/{admin_me['id']}/status", json={"is_active": False}, headers=HA)
    check("管理", "自我保护（禁用自己被拒 400）", r.status_code == 400, f"HTTP {r.status_code}")

    # 边界：操作不存在的用户
    r = client.put(f"{BASE}/api/admin/users/999999/status", json={"is_active": False}, headers=HA)
    check("管理", "边界（操作不存在用户 404）", r.status_code == 404, f"HTTP {r.status_code}")

    # 内容治理：列表 + 关键词 + 下架恢复
    r = client.get(f"{BASE}/api/admin/contents", params={"type": "supply", "status": "active"}, headers=HA)
    act = r.json()["list"]
    check("管理", "内容治理列表（供应 active）", r.status_code == 200 and len(act) >= 1)
    if act:
        sid = act[0]["id"]
        kw = act[0]["title"][:2]
        r = client.get(f"{BASE}/api/admin/contents", params={"type": "supply", "keyword": kw}, headers=HA)
        kw_ok = any(x["id"] == sid for x in r.json()["list"])
        check("管理", "内容治理（关键词搜索）", kw_ok, f"kw={kw}")

        client.put(f"{BASE}/api/admin/contents/supply/{sid}/status", json={"status": "offline"}, headers=HA)
        r = client.get(f"{BASE}/api/admin/contents", params={"type": "supply", "status": "offline"}, headers=HA)
        off_ok = any(x["id"] == sid for x in r.json()["list"])
        client.put(f"{BASE}/api/admin/contents/supply/{sid}/status", json={"status": "active"}, headers=HA)
        check("管理", "强制下架 + 恢复上架", off_ok)

    # 政策文档列表（知识库管理）
    r = client.get(f"{BASE}/api/admin/policy-docs", headers=HA)
    docs = r.json()
    check("管理", "政策文档列表（ready 文档与分块）",
          r.status_code == 200 and sum(1 for d in docs if d["status"] == "ready") >= 3
          and sum(d["chunk_count"] or 0 for d in docs) >= 3, f"{len(docs)}个文档")

    # 权限矩阵：farmer 访问 admin 接口
    for path in ("/api/admin/stats", "/api/admin/users", "/api/admin/contents?type=supply",
                 "/api/admin/policy-docs"):
        r = client.get(f"{BASE}{path}", headers=HF)
        if r.status_code != 403:
            check("管理", "权限矩阵（farmer 访问 admin 接口应403）", False, f"{path} → {r.status_code}")
            break
    else:
        check("管理", "权限矩阵（farmer 访问 admin 接口全部 403）", True)

    # admin 使用农技问答（昨天新加的入口对应后端能力）
    r = client.post(f"{BASE}/api/sessions", json={"type": "agritech"}, headers=HA)
    s_admin_agri = r.json()
    text_a, _, err_a, _ = sse_post(
        client, f"{BASE}/api/agritech/chat", admin_tok,
        {"session_id": s_admin_agri["id"], "content": "草莓灰霉病怎么防治？"},
    )
    check("农技AI", "admin 角色使用农技问答（新增入口验证）", not err_a and len(text_a) > 80,
          err_a or f"{len(text_a)}字")

    # ══════════ 清理 ══════════
    r = client.delete(f"{BASE}/api/sessions/{s_agri['id']}", headers={"Authorization": f"Bearer {regr_tok}"})
    client.delete(f"{BASE}/api/sessions/{s_pol['id']}", headers=HF)
    client.delete(f"{BASE}/api/sessions/{s_admin_agri['id']}", headers=HA)
    check("会话", "删除会话（清理）", r.status_code in (200, 204), f"HTTP {r.status_code}")

    # ══════════ 汇总 ══════════
    dur = round(time.time() - t_all, 1)
    total = len(RESULTS)
    passed = sum(1 for x in RESULTS if x["status"] == "pass")
    failed = [x for x in RESULTS if x["status"] == "fail"]
    summary = {
        "date": TODAY,
        "round": 2,
        "duration_sec": dur,
        "total": total,
        "passed": passed,
        "failed": len(failed),
        "pass_rate": round(passed / total * 100, 1),
        "results": RESULTS,
    }
    Path("data/regression_result2.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n{'=' * 46}\n第二轮结果：{passed}/{total} 通过（{summary['pass_rate']}%），耗时 {dur}s")
    if failed:
        print("失败用例：")
        for f_ in failed:
            print(f"  ✘ [{f_['module']}] {f_['name']} —— {f_['detail']}")
    print("明细已写入 data/regression_result2.json")
    return 0 if not failed else 1


if __name__ == "__main__":
    raise SystemExit(main())
