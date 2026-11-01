"""政策问答 LangGraph 图：retrieve → generate 两节点。

retrieve：问题向量化 → 余弦检索 Top-5 分块 → 拼装【政策资料】
generate：资料 + 历史上下文 → qwen-plus 流式生成

流式：调用方通过 graph.astream_events(version="v2") 监听
on_chat_model_stream 事件获取逐 token 增量（retrieve 节点无 LLM 调用，不产生事件）。
"""
from langchain_core.messages import BaseMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from app.database import SessionLocal
from app.services.llm import get_text_llm
from app.services.rag import build_context, search_chunks

POLICY_SYSTEM_PROMPT = """你是惠农政策咨询助手，只依据提供的政策资料回答问题。

规则：
1. 只使用【政策资料】中的内容回答，可适度组织语言但不得添加资料外的信息；
2. 回答末尾注明依据的政策文档名称；
3. 资料中没有相关内容时，明确回答"当前知识库暂无此政策信息"，不编造；
4. 涉及补贴金额、申请条件、截止日期等关键数字时，原样引用资料原文。

【政策资料】
{context}"""

EMPTY_CONTEXT_PROMPT = """你是惠农政策咨询助手。当前知识库中没有检索到与用户问题相关的政策资料。

请直接回答"当前知识库暂无此政策信息"，并建议用户咨询当地农业农村局了解最新政策。
回答保持简短（1-2 句），不要编造任何政策内容。"""


class PolicyState(TypedDict):
    messages: list[BaseMessage]  # 历史上下文（含本条用户消息）
    question: str
    context: str  # 检索到的【政策资料】
    answer: str


async def retrieve_node(state: PolicyState) -> dict:
    """向量检索 Top-5 分块，拼装资料上下文。"""
    with SessionLocal() as db:
        chunks = await search_chunks(db, state["question"])
    context, _ = build_context(chunks)
    return {"context": context}


async def generate_node(state: PolicyState) -> dict:
    # 无资料时切换提示词（规则 3：明确说明无信息，不编造），仍走 LLM 保持流式一致
    if state.get("context"):
        system = POLICY_SYSTEM_PROMPT.format(context=state["context"])
    else:
        system = EMPTY_CONTEXT_PROMPT

    messages = [SystemMessage(content=system)]
    messages.extend(state["messages"])
    resp = await get_text_llm().ainvoke(messages)
    return {"answer": resp.content}


def build_policy_graph():
    g = StateGraph(PolicyState)
    g.add_node("retrieve", retrieve_node)
    g.add_node("generate", generate_node)
    g.add_edge(START, "retrieve")
    g.add_edge("retrieve", "generate")
    g.add_edge("generate", END)
    return g.compile()


# 模块级编译一次
policy_graph = build_policy_graph()
