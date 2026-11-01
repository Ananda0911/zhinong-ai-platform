"""政策 RAG：分块入库 + 向量检索（SQLite BLOB + NumPy 余弦 Top-K）。

设计文档 3.4：量级为几十份文档、数千 chunk，全量内存检索 <10ms，
不接 FAISS/Chroma；量级上来可整体替换为 sqlite-vec / Milvus VectorStore。
"""
import numpy as np
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import PolicyChunk, PolicyDoc
from app.services.embedding import embed_text

_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)


async def chunk_and_store(db: Session, doc_id: int, markdown: str) -> int:
    """Markdown → 分块 → 逐块向量化入库。返回块数（失败抛异常）。"""
    chunks = _splitter.split_text(markdown)
    if not chunks:
        raise ValueError("文档分块结果为空")
    for idx, text in enumerate(chunks):
        embedding = await embed_text(text)
        db.add(PolicyChunk(doc_id=doc_id, chunk_index=idx, content=text, embedding=embedding))
    return len(chunks)


async def search_chunks(db: Session, query: str, top_k: int = 5) -> list[PolicyChunk]:
    """问题 → 向量 → 全量余弦 → Top-K（只检索 ready 文档的分块）。

    joinedload 预加载 doc，避免 session 关闭后访问来源标题触发 lazy load。
    """
    rows = db.scalars(
        select(PolicyChunk)
        .join(PolicyDoc)
        .options(joinedload(PolicyChunk.doc))
        .where(PolicyDoc.status == "ready")
    ).all()
    rows = [r for r in rows if r.embedding]
    if not rows:
        return []

    q = np.frombuffer(await embed_text(query), dtype=np.float32)
    mat = np.vstack([np.frombuffer(r.embedding, dtype=np.float32) for r in rows])
    norms = np.linalg.norm(mat, axis=1) * np.linalg.norm(q)
    sims = mat @ q / np.where(norms == 0, 1e-9, norms)

    top = np.argsort(-sims)[:top_k]
    return [rows[i] for i in top if sims[i] > 0.3]  # 相似度过低的直接丢弃


def build_context(chunks: list[PolicyChunk]) -> tuple[str, list[str]]:
    """拼装【政策资料】文本 + 去重来源文档标题。"""
    lines = []
    for c in chunks:
        title = c.doc.title if c.doc else "未知文档"
        lines.append(f"【{title}】{c.content}")
    sources = []
    for c in chunks:
        if c.doc and c.doc.title not in sources:
            sources.append(c.doc.title)
    return "\n\n".join(lines), sources
