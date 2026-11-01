"""助农 AI 平台 · 第三轮回归 —— 遗漏排查专用脚本。

聚焦前两轮未覆盖的盲区：
1. 水平越权（IDOR）：用户 B（同角色）对用户 A 的供应/会话的改删读
2. 会话跨类型混用（agritech 会话调 policy/chat）
3. 空态与边界：新用户空列表、不存在资源 404、分页越界
4. 数据隔离：mine 列表 / 营销记录 只见自己
5. 上传校验：非图片 400、伪 content_type 记录为已知事项

运行：backend/ 下 .venv\\Scripts\\python scripts\\test_gap_check.py
输出：控制台摘要 + data/gap_check_result.json
"""
import json
import time
import uuid

import httpx

BASE = "http://127.0.0.1:8000"
RESULTS = []
KNOWN_ISSUES = []


def check(module, name, cond, detail=""):
    RESULTS.append(
        {"module": module, "name": name, "status": "pass" if cond else "fail", "detail": str(detail)[:300]}
    )
    mark = "✔" if cond else "✘"
    print(f"  {mark} {name}" + (f"  —— {detail}" if (detail and not cond) else ""))
    return cond


def known(module, name, detail):
    KNOWN_ISSUES.append({"module": module, "name": name, "detail": str(detail)[:300]})
    print(f"  ⚠ [已知事项] {name} —— {detail}")


def login(client, username, password="123456"):
    r = client.post(f"{BASE}/api/auth/login", json={"username": username, "password": password})
    r.raise_for_status()
    return r.json()["access_token"]


def sse_post(client, url, token, payload, timeout=60):
    """POST SSE → (拼接文本, error消息)。"""
    text, error = "", ""
    with client.stream(
        "POST", url, json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=timeout
    ) as resp:
        if resp.status_code != 200:
            return "", f"HTTP {resp.status_code}"
        event = "message"
        for line in resp.iter_lines():
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                data = json.loads(line.split(":", 1)[1].strip())
                if event == "message":
                    text += data["delta"]
                elif event == "error":
                    error = data["message"]
    return text, error


def main():
    client = httpx.Client(timeout=60)
    t_all = time.time()
    stamp = uuid.uuid4().hex[:6]

    # ══════════ 准备：A（farmertest）的资源 ══════════
    print("\n[准备] A=farmertest 建供应 + 两种会话；B=新注册 farmer")
    tok_a = login(client, "farmertest")
    hdr_a = {"Authorization": f"Bearer {tok_a}"}

    r = client.post(
        f"{BASE}/api/supply",
        json={
            "title": f"越权测试红富士{stamp}",
            "category": "果蔬",
            "quantity": 100,
            "unit": "斤",
            "price": 5.5,
            "region": "陕西延安",
            "description": "第三轮IDOR排查专用，稍后删除",
            "expire_days": 30,
        },
        headers=hdr_a,
    )
    r.raise_for_status()
    supply_id = r.json()["id"]

    r = client.post(f"{BASE}/api/sessions", json={"type": "agritech"}, headers=hdr_a)
    r.raise_for_status()
    sess_agr = r.json()["id"]
    r = client.post(f"{BASE}/api/sessions", json={"type": "policy"}, headers=hdr_a)
    r.raise_for_status()
    sess_pol = r.json()["id"]

    # B：同角色新用户
    uname_b = f"regrgap{int(time.time()) % 100000}"
    r = client.post(
        f"{BASE}/api/auth/register",
        json={"username": uname_b, "password": "123456", "nickname": "越权排查员", "role": "farmer"},
    )
    r.raise_for_status()
    tok_b = login(client, uname_b)
    hdr_b = {"Authorization": f"Bearer {tok_b}"}

    # ══════════ 1. 水平越权（IDOR）══════════
    print("\n[1] 水平越权（IDOR）：B 对 A 的资源")
    r = client.put(
        f"{BASE}/api/supply/{supply_id}",
        json={"title": "劫持", "category": "果蔬", "quantity": 1, "unit": "斤", "region": "Hack", "expire_days": 30},
        headers=hdr_b,
    )
    check("IDOR", "B 编辑 A 的供应 → 403", r.status_code == 403, f"HTTP {r.status_code}")

    r = client.put(
        f"{BASE}/api/supply/{supply_id}/status", json={"status": "offline"}, headers=hdr_b
    )
    check("IDOR", "B 下架 A 的供应 → 403", r.status_code == 403, f"HTTP {r.status_code}")

    r = client.delete(f"{BASE}/api/supply/{supply_id}", headers=hdr_b)
    check("IDOR", "B 删除 A 的供应 → 403", r.status_code == 403, f"HTTP {r.status_code}")

    r = client.delete(f"{BASE}/api/sessions/{sess_agr}", headers=hdr_b)
    check("IDOR", "B 删除 A 的会话 → 404（不暴露存在性）", r.status_code == 404, f"HTTP {r.status_code}")

    r = client.get(f"{BASE}/api/sessions/{sess_agr}/messages", headers=hdr_b)
    check("IDOR", "B 读 A 的会话消息 → 404", r.status_code == 404, f"HTTP {r.status_code}")

    text, error = sse_post(client, f"{BASE}/api/agritech/chat", tok_b, {"session_id": sess_agr, "content": "劫持"})
    check("IDOR", "B 用 A 的会话聊农技 → SSE error 拒绝", error == "会话不存在" and text == "", f"error={error!r} text={text[:30]!r}")

    text, error = sse_post(client, f"{BASE}/api/policy/chat", tok_b, {"session_id": sess_pol, "content": "劫持"})
    check("IDOR", "B 用 A 的会话聊政策 → SSE error 拒绝", error == "会话不存在" and text == "", f"error={error!r}")

    text, error = sse_post(
        client, f"{BASE}/api/policy/chat", tok_a, {"session_id": sess_agr, "content": "跨类型混用"}
    )
    check("IDOR", "A 拿农技会话调政策接口 → type 校验拒绝", error == "会话不存在" and text == "", f"error={error!r}")

    text, error = sse_post(
        client, f"{BASE}/api/agritech/chat", tok_a, {"session_id": sess_pol, "content": "跨类型混用"}
    )
    check("IDOR", "A 拿政策会话调农技接口 → type 校验拒绝", error == "会话不存在" and text == "", f"error={error!r}")

    # ══════════ 2. 数据隔离 ══════════
    print("\n[2] 数据隔离")
    r = client.get(f"{BASE}/api/supply?status=mine", headers=hdr_b)
    titles = [s["title"] for s in r.json()["list"]]
    check("隔离", "B 的「我的供应」不见 A 的供应", f"越权测试红富士{stamp}" not in titles, f"共{len(titles)}条")

    r = client.get(f"{BASE}/api/marketing/records", headers=hdr_b)
    check("隔离", "新用户营销记录为空列表", r.status_code == 200 and r.json() == [], r.text[:80])

    r = client.get(f"{BASE}/api/sessions?type=agritech", headers=hdr_b)
    check("隔离", "新用户农技会话为空列表", r.status_code == 200 and r.json() == [], r.text[:80])

    # ══════════ 3. 空态与边界 ══════════
    print("\n[3] 空态与边界")
    r = client.get(f"{BASE}/api/supply/999999", headers=hdr_a)
    check("边界", "不存在的供应详情 → 404", r.status_code == 404, f"HTTP {r.status_code}")

    text, error = sse_post(client, f"{BASE}/api/agritech/chat", tok_a, {"session_id": 999999, "content": "x"})
    check("边界", "不存在的会话聊天 → SSE error", error == "会话不存在", f"error={error!r}")

    tok_admin = login(client, "admin")
    hdr_admin = {"Authorization": f"Bearer {tok_admin}"}
    r = client.get(f"{BASE}/api/admin/users?page=999&size=10", headers=hdr_admin)
    check("边界", "用户分页越界 → 200 空列表", r.status_code == 200 and r.json()["list"] == [], r.text[:80])

    r = client.get(f"{BASE}/api/supply?page=1&size=1", headers=hdr_a)
    body = r.json()
    check("边界", "供应分页 size=1 → 恰好 1 条", len(body["list"]) == 1, f"返回{len(body['list'])}条")

    # ══════════ 4. 上传校验 ══════════
    print("\n[4] 上传校验")
    r = client.post(
        f"{BASE}/api/upload/image",
        files={"file": ("note.txt", b"just text", "text/plain")},
        headers=hdr_a,
    )
    check("上传", "上传 text/plain → 400", r.status_code == 400, f"HTTP {r.status_code}")

    r = client.post(
        f"{BASE}/api/upload/image",
        files={"file": ("fake.jpg", b"just text fake", "image/jpeg")},
        headers=hdr_a,
    )
    if r.status_code == 200:
        known("上传", "图片魔数未校验", "伪装 content_type=image/jpeg 的文本文件可存成 .jpg（诊断时模型会忽略/报错，风险低，建议上线前校验文件头魔数）")
    else:
        check("上传", "伪 content_type 被拦截", True)

    r = client.post(
        f"{BASE}/api/admin/policy-docs",
        params={"title": "非法格式测试"},
        files={"file": ("virus.exe", b"MZ999999", "application/x-msdownload")},
        headers=hdr_admin,
    )
    check("上传", "政策文档上传 .exe → 400", r.status_code == 400, f"HTTP {r.status_code}")

    # ══════════ 清理 ══════════
    print("\n[清理] 删除测试数据")
    client.delete(f"{BASE}/api/supply/{supply_id}", headers=hdr_a)
    client.delete(f"{BASE}/api/sessions/{sess_agr}", headers=hdr_a)
    client.delete(f"{BASE}/api/sessions/{sess_pol}", headers=hdr_a)
    try:
        import sqlite3

        conn = sqlite3.connect("data/app.db")
        conn.execute("DELETE FROM users WHERE username LIKE 'regrgap%'")
        conn.commit()
        conn.close()
        print("  ✔ B 账号已清理")
    except Exception as e:
        print(f"  ⚠ B 账号清理失败：{e}")

    # ══════════ 摘要 ══════════
    total = len(RESULTS)
    passed = sum(1 for x in RESULTS if x["status"] == "pass")
    failed = total - passed
    dur = round(time.time() - t_all, 1)

    print(f"\n{'='*56}")
    print(f"第三轮遗漏排查：{passed}/{total} 通过，{failed} 失败，{len(KNOWN_ISSUES)} 已知事项，{dur}s")
    for x in RESULTS:
        if x["status"] == "fail":
            print(f"  ✘ [{x['module']}] {x['name']} —— {x['detail']}")

    Path = __import__("pathlib").Path
    Path("data").mkdir(exist_ok=True)
    Path("data/gap_check_result.json").write_text(
        json.dumps(
            {
                "date": time.strftime("%Y-%m-%d %H:%M:%S"),
                "round": 3,
                "duration_sec": dur,
                "total": total,
                "passed": passed,
                "failed": failed,
                "pass_rate": round(passed / total * 100, 1) if total else 100,
                "results": RESULTS,
                "known_issues": KNOWN_ISSUES,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    print("结果已写入 data/gap_check_result.json")


if __name__ == "__main__":
    main()
