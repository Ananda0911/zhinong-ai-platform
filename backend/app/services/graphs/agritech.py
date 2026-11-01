"""农技 AI 助手 LangGraph 图：文本问答 / 病虫害图片诊断 双分支。

流式：调用方通过 graph.astream_events(version="v2") 监听
on_chat_model_stream 事件获取逐 token 增量。
"""
from langchain_core.messages import BaseMessage
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from app.services.llm import get_text_llm, get_vl_llm

AGRITECH_SYSTEM_PROMPT = """你是一位经验丰富的农业技术专家，为农户和合作社工作人员提供种植、养殖技术指导。

要求：
1. 回答实用、具体、可操作，分点说明关键步骤；
2. 用通俗易懂的语言，避免不必要的专业术语，出现术语时用一句话解释；
3. 涉及用药时，必须提醒安全间隔期和用量限制；
4. 信息不足时先追问关键细节（如作物品种、生长阶段、地区），再给建议；
5. 不确定时明确说明，不编造；遇到超出农业范围的问题，礼貌拒绝。"""

DIAGNOSE_SYSTEM_PROMPT = """你是农作物病虫害诊断专家。用户会上传作物照片（可能附文字说明）。
请按以下结构输出诊断结果：

【诊断结论】判断是病害/虫害/生理性问题时，给出最可能的 1-2 个具体名称及置信程度
【症状依据】照片中观察到的关键症状
【成因分析】可能的诱因（气候、土壤、管理等）
【防治方案】分"农业防治""化学/生物防治"两部分，具体到药剂名称与浓度
【用药提示】安全间隔期、轮换用药等注意事项
【严重程度】轻度/中度/重度，及是否建议求助当地农技部门

若照片与作物病虫害无关，说明无法诊断并引导用户重新拍摄。"""


class AgritechState(TypedDict):
    messages: list[BaseMessage]  # system + 历史上下文 + 本条用户消息
    image_data_url: str | None  # 有图走 qwen-vl 诊断分支
    answer: str


def _route(state: AgritechState) -> str:
    return "diagnose" if state.get("image_data_url") else "chat"


async def chat_node(state: AgritechState) -> dict:
    resp = await get_text_llm().ainvoke(state["messages"])
    return {"answer": resp.content}


async def diagnose_node(state: AgritechState) -> dict:
    resp = await get_vl_llm().ainvoke(state["messages"])
    return {"answer": resp.content}


def build_agritech_graph():
    g = StateGraph(AgritechState)
    g.add_node("chat", chat_node)
    g.add_node("diagnose", diagnose_node)
    g.add_conditional_edges(START, _route, {"chat": "chat", "diagnose": "diagnose"})
    g.add_edge("chat", END)
    g.add_edge("diagnose", END)
    return g.compile()


# 模块级编译一次
agritech_graph = build_agritech_graph()
