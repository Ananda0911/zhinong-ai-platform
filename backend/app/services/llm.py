"""LLM 统一封装：通义千问（DashScope OpenAI 兼容模式）经 langchain-openai 接入。

模型名集中在 config.py，业务代码只 import 本模块。
"""
from langchain_openai import ChatOpenAI

from app.config import settings


def get_text_llm() -> ChatOpenAI:
    """文本对话模型（qwen-plus），流式。"""
    return ChatOpenAI(
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.DASHSCOPE_BASE_URL,
        model=settings.MODEL_TEXT,
        streaming=True,
        timeout=60,
    )


def get_vl_llm() -> ChatOpenAI:
    """视觉模型（qwen-vl-plus），用于病虫害图片识别。"""
    return ChatOpenAI(
        api_key=settings.DASHSCOPE_API_KEY,
        base_url=settings.DASHSCOPE_BASE_URL,
        model=settings.MODEL_VL,
        streaming=True,
        timeout=90,
    )


async def chat_stream(messages: list):
    """流式对话：逐 token yield 文本增量（LangGraph 节点内通用）。"""
    llm = get_text_llm()
    async for evt in llm.astream_events(messages, version="v2"):
        if evt["event"] == "on_chat_model_stream":
            content = evt["data"]["chunk"].content
            if content:
                yield content
