"""营销文案生成 LangGraph 图：单节点（qwen-plus），按 gen_type 切换输出形态。

流式：调用方通过 graph.astream_events(version="v2") 监听
on_chat_model_stream 事件获取逐 token 增量。
"""
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from typing_extensions import TypedDict

from app.services.llm import get_text_llm

MARKETING_SYSTEM_PROMPT = """你是农产品电商营销专家，深谙电商平台、直播带货和短视频运营的爆款方法论。
你写的文案：真实可信、突出农产品卖点、贴近消费者生活，遵守《广告法》
（不用"最好""第一""国家级"等极限词，不夸大功效）。输出使用 Markdown 格式。"""

# 三种生成类型的具体要求（拼入 user prompt）
GEN_TYPE_BRIEF = {
    "detail": (
        "请生成一份商品详情页文案，包含：\n"
        "1. 一个吸引人的商品标题（20 字内）\n"
        "2. 3-5 个卖点短句（每条 15 字内，可直接用作主图标签）\n"
        "3. 分段的详情介绍（产地故事、种植/养殖方式、口感/品质、适用场景）\n"
        "4. 5-8 个建议的商品搜索标签"
    ),
    "live": (
        "请生成一份直播带货话术，按 4 个阶段组织，每阶段给出可直接照读的口语化文本：\n"
        "1. 开场引流（欢迎、留人、预告福利）\n"
        "2. 产品介绍（产地与种植故事、口感体验、现场试吃话术）\n"
        "3. 促单话术（价格对比、限时限量、下单引导）\n"
        "4. 互动答疑预设（常见问题 + 标准回答，至少 3 组）"
    ),
    "video": (
        "请生成一份约 60 秒的短视频分镜头脚本，用表格输出，列：镜号 | 时长 | 画面描述 | 口播文案。\n"
        "要求：开头 3 秒有钩子，口播口语化、有节奏感，结尾引导关注/下单。"
    ),
}

TONE_PRESETS = ("接地气", "突出产地故事", "强调绿色健康", "高端礼盒", "家常亲切", "年轻活泼")


def build_marketing_messages(
    product_name: str,
    category: str,
    gen_type: str,
    features: str | None = None,
    selling_points: str | None = None,
    tone: str | None = None,
) -> list[BaseMessage]:
    """组装 system + user 消息（gen_type 决定输出形态）。"""
    lines = [
        f"请为以下农产品生成营销内容。",
        "",
        f"产品名称：{product_name}",
        f"类目：{category}",
    ]
    if features:
        lines.append(f"产品特点：{features}")
    if selling_points:
        lines.append(f"核心卖点：{selling_points}")
    lines.append(f"风格要求：{tone or '接地气，真实可信'}")
    lines.append("")
    lines.append(GEN_TYPE_BRIEF[gen_type])
    return [SystemMessage(content=MARKETING_SYSTEM_PROMPT), HumanMessage(content="\n".join(lines))]


class MarketingState(TypedDict):
    messages: list[BaseMessage]
    answer: str


async def generate_node(state: MarketingState) -> dict:
    resp = await get_text_llm().ainvoke(state["messages"])
    return {"answer": resp.content}


def build_marketing_graph():
    g = StateGraph(MarketingState)
    g.add_node("generate", generate_node)
    g.add_edge(START, "generate")
    g.add_edge("generate", END)
    return g.compile()


# 模块级编译一次
marketing_graph = build_marketing_graph()
