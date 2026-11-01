"""Phase 4 联调验收：营销生成 + 政策文档上传解析 + RAG 问答。

运行：backend/ 下 .venv\\Scripts\\python scripts\\test_phase4.py
前置：后端 8000 端口运行中；farmertest/admin 账号存在（密码 123456）。
"""
import sys
import time
from pathlib import Path

import httpx

BASE = "http://127.0.0.1:8000"

# ── 测试政策文档（内容含具体金额/条件/日期，供 RAG 检索验证）──
POLICY_TEXT = """2026年实际种粮农民一次性补贴实施方案

一、补贴对象
实际种粮农民，包括利用自有承包地种粮的农民，以及流转土地种粮的大户、
家庭农场、农民合作社、农业企业等新型农业经营主体。

二、补贴标准
按实际种植面积计算，每亩补贴120元。对种植双季稻的，早稻每亩额外补贴50元。
单个主体补贴上限为100万元。

三、申请流程
1. 7月15日前向村委会提交申请表、土地流转合同复印件、身份证复印件；
2. 村级公示7天后报乡镇农业农村办审核；
3. 县农业农村局复核，8月31日前通过"一卡通"发放到户。

四、农机购置补贴
购置列入目录的农机，按购置价的30%给予补贴，单台补贴上限5万元。
拖拉机和联合收割机需办理牌证后方可申请。

五、监督管理
对虚报种植面积的，取消3年补贴资格并追回已发补贴资金。
"""


def login(client: httpx.Client, username: str) -> str:
    r = client.post(f"{BASE}/api/auth/login", json={"username": username, "password": "123456"})
    r.raise_for_status()
    return r.json()["access_token"]


def sse_post(client: httpx.Client, url: str, token: str, payload: dict) -> tuple[str, dict]:
    """POST SSE，返回 (拼接文本, done 事件 data)。"""
    text, done, error = "", {}, ""
    with client.stream(
        "POST",
        url,
        json=payload,
        headers={"Authorization": f"Bearer {token}"},
        timeout=120,
    ) as resp:
        assert resp.status_code == 200, f"{url} HTTP {resp.status_code}"
        event = "message"
        for line in resp.iter_lines():
            if line.startswith("event:"):
                event = line.split(":", 1)[1].strip()
            elif line.startswith("data:"):
                import json

                data = json.loads(line.split(":", 1)[1].strip())
                if event == "message":
                    text += data["delta"]
                elif event == "done":
                    done = data
                elif event == "error":
                    error = data["message"]
    if error:
        raise AssertionError(f"{url} SSE error: {error}")
    return text, done


def main():
    client = httpx.Client()

    # ── 1. 营销文案生成（detail）──
    farmer_token = login(client, "farmertest")
    print("[1/6] 营销文案生成（detail，SSE 流式）……")
    text, done = sse_post(
        client,
        f"{BASE}/api/marketing/generate",
        farmer_token,
        {
            "product_name": "洛川红富士苹果",
            "category": "果蔬",
            "features": "陕西洛川高原红富士，海拔1100米，昼夜温差大，自然生长180天",
            "selling_points": "脆甜多汁\n现摘现发\n坏果包赔",
            "gen_type": "detail",
            "tone": "突出产地故事",
        },
    )
    assert done.get("record_id"), "缺 record_id"
    assert "洛川" in text and len(text) > 200, f"文案质量异常：{text[:80]}"
    print(f"      ok：record_id={done['record_id']}，{len(text)} 字，含产地关键词")

    # ── 2. 生成历史 ──
    print("[2/6] 生成历史查询……")
    r = client.get(
        f"{BASE}/api/marketing/records", headers={"Authorization": f"Bearer {farmer_token}"}
    )
    r.raise_for_status()
    records = r.json()
    assert any(x["id"] == done["record_id"] for x in records), "历史中未找到刚生成的记录"
    print(f"      ok：共 {len(records)} 条历史")

    # ── 3. admin 上传政策文档（txt，本地直读，无需 MinerU token）──
    print("[3/6] 上传政策文档（txt）……")
    admin_token = login(client, "admin")
    tmp = Path("data/_test_policy.txt")
    tmp.write_text(POLICY_TEXT, encoding="utf-8")
    with open(tmp, "rb") as f:
        r = client.post(
            f"{BASE}/api/admin/policy-docs",
            params={"title": "2026年实际种粮农民一次性补贴实施方案"},
            files={"file": ("种粮补贴方案.txt", f, "text/plain")},
            headers={"Authorization": f"Bearer {admin_token}"},
        )
    r.raise_for_status()
    doc_id = r.json()["id"]
    print(f"      ok：doc_id={doc_id}，status=processing")

    # ── 4. 轮询解析完成（txt 直读 + embedding，约几秒）──
    print("[4/6] 等待后台解析（分块 + 向量化）……")
    for _ in range(30):
        r = client.get(
            f"{BASE}/api/admin/policy-docs", headers={"Authorization": f"Bearer {admin_token}"}
        )
        doc = next((d for d in r.json() if d["id"] == doc_id), None)
        if doc and doc["status"] != "processing":
            break
        time.sleep(1)
    assert doc["status"] == "ready", f"解析未就绪：{doc}"
    assert doc["chunk_count"] > 0, "分块数为 0"
    print(f"      ok：status=ready，{doc['chunk_count']} 个分块")

    # ── 5. RAG 问答（文档内有答案的问题）──
    print("[5/6] 政策 RAG 问答（补贴标准）……")
    r = client.post(
        f"{BASE}/api/sessions",
        json={"type": "policy"},
        headers={"Authorization": f"Bearer {farmer_token}"},
    )
    r.raise_for_status()
    session_id = r.json()["id"]
    answer, done = sse_post(
        client,
        f"{BASE}/api/policy/chat",
        farmer_token,
        {"session_id": session_id, "content": "种粮农民一次性补贴每亩多少钱？"},
    )
    assert "120" in answer, f"回答未引用文档金额：{answer[:120]}"
    assert "种粮补贴方案" in answer or "种粮农民一次性补贴" in answer, f"未注明依据文档：{answer[-100:]}"
    print(f"      ok：回答引用了每亩120元 + 文档来源，{len(answer)} 字")

    # ── 6. 知识库外问题（应答"暂无"）──
    print("[6/6] 知识库外问题（不编造）……")
    answer2, _ = sse_post(
        client,
        f"{BASE}/api/policy/chat",
        farmer_token,
        {"session_id": session_id, "content": "农村宅基地翻建需要什么手续？"},
    )
    assert "暂无" in answer2, f"知识库外回答异常：{answer2[:120]}"
    print(f"      ok：明确回复暂无信息（{answer2[:40]}…）")

    tmp.unlink(missing_ok=True)
    print("\nPhase 4 验收全部通过 ✔")


if __name__ == "__main__":
    sys.exit(main())
