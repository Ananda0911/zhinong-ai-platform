"""LangGraph 冒烟测试：验证通义千问连通 + LangGraph 编排可用。

用法（在 backend 目录下）：
    .venv\\Scripts\\python scripts\\smoke_test_langgraph.py

前提：.env 中 DASHSCOPE_API_KEY 已填写真实 key。
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from app.config import settings
from app.services.llm import get_text_llm


class SmokeState(TypedDict):
    messages: list
    answer: str


def ask_node(state: SmokeState) -> SmokeState:
    llm = get_text_llm()
    resp = llm.invoke(state["messages"])
    return {"answer": resp.content}


def build_graph():
    g = StateGraph(SmokeState)
    g.add_node("ask", ask_node)
    g.add_edge(START, "ask")
    g.add_edge("ask", END)
    return g.compile()


async def main():
    if not settings.DASHSCOPE_API_KEY or settings.DASHSCOPE_API_KEY.startswith("sk-your"):
        print("[SKIP] 未配置 DASHSCOPE_API_KEY，请在 backend/.env 填写后重试")
        return

    graph = build_graph()
    print("[1/2] LangGraph 图构建成功，正在调用通义千问（qwen-plus）……")
    result = await graph.ainvoke(
        {
            "messages": [
                SystemMessage(content="你是一个冒烟测试助手，只回复一句话。"),
                HumanMessage(content="请回复：助农AI平台 LangGraph 冒烟测试通过"),
            ],
            "answer": "",
        }
    )
    print(f"[2/2] 模型回复：{result['answer']}")

    # 顺带验证流式
    from app.services.llm import chat_stream

    print("\n流式输出测试：")
    async for delta in chat_stream([HumanMessage(content="用 20 字解释什么是 RAG")]):
        print(delta, end="", flush=True)
    print("\n\n冒烟测试全部通过 ✔")


if __name__ == "__main__":
    asyncio.run(main())
