"""向量化服务：text-embedding-v3（DashScope 兼容端点）+ 余弦相似度。

向量以 float32 BLOB 存 SQLite，检索时全量加载到内存计算（量级小，<10ms）。
"""
import numpy as np
from langchain_openai import OpenAIEmbeddings

from app.config import settings

_embeddings = OpenAIEmbeddings(
    api_key=settings.DASHSCOPE_API_KEY,
    base_url=settings.DASHSCOPE_BASE_URL,
    model=settings.MODEL_EMBEDDING,
    # 关键：禁用 tiktoken 分词（DashScope 只接受字符串输入，不接受 token 数组）
    check_embedding_ctx_length=False,
)


async def embed_text(text: str) -> bytes:
    """文本 → float32 向量 bytes。失败抛异常（调用方决定如何处理）。"""
    vec = await _embeddings.aembed_query(text)
    return np.asarray(vec, dtype=np.float32).tobytes()


def cosine_sim(blob_a: bytes | None, blob_b: bytes | None) -> float:
    """两个 BLOB 向量的余弦相似度。"""
    if not blob_a or not blob_b:
        return 0.0
    a = np.frombuffer(blob_a, dtype=np.float32)
    b = np.frombuffer(blob_b, dtype=np.float32)
    if a.shape != b.shape:
        return 0.0
    norm = np.linalg.norm(a) * np.linalg.norm(b)
    if norm == 0:
        return 0.0
    return float(np.dot(a, b) / norm)


def score_level(score: float) -> str:
    """匹配度分级：高 ≥0.75 / 中 0.5-0.75 / 低 <0.5。"""
    if score >= 0.75:
        return "high"
    if score >= 0.5:
        return "mid"
    return "low"
