"""政策 RAG：分块入库 + FAISS 向量检索。

链路：SQLite BLOB 持久化 + FAISS IndexIDMap2(IndexFlatIP) 内存索引。
- 入库：chunk_and_store 落库后实时 add 进索引
- 检索：search_chunks 走 FAISS Top-K（归一化内积 = 余弦），
  命中 id 回 DB 取全文（joinedload 预加载 doc），<0.3 低分丢弃
- 删除：文档删除时 remove（admin.delete_policy_doc）
- 启动：rebuild_policy_index 全量重建（main.startup 调用）
"""
from langchain_text_splitters import RecursiveCharacterTextSplitter
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.models import PolicyChunk, PolicyDoc
from app.services.embedding import embed_text
from app.services.vector_index import VectorIndex

_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

# 政策分块索引（进程内共享，uvicorn 单进程）
policy_index = VectorIndex()


def rebuild_policy_index(db: Session) -> int:
    """从 SQLite 全量重建政策分块索引（只含 ready 文档）。返回索引条数。"""
    rows = db.execute(
        select(PolicyChunk.id, PolicyChunk.embedding)
        .join(PolicyDoc)
        .where(PolicyDoc.status == "ready", PolicyChunk.embedding.isnot(None))
    ).all()
    policy_index.rebuild([(r[0], r[1]) for r in rows])
    return len(rows)


async def chunk_and_store(db: Session, doc_id: int, markdown: str) -> int:
    """Markdown → 分块 → 逐块向量化入库（落库 + 同步 FAISS）。返回块数。"""
    chunks = _splitter.split_text(markdown)
    if not chunks:
        raise ValueError("文档分块结果为空")
    for idx, text in enumerate(chunks):
        embedding = await embed_text(text)
        chunk = PolicyChunk(doc_id=doc_id, chunk_index=idx, content=text, embedding=embedding)
        db.add(chunk)
        db.flush()  # 取自增 id 供索引使用
        policy_index.add(chunk.id, embedding)
    return len(chunks)


async def search_chunks(db: Session, query: str, top_k: int = 5) -> list[PolicyChunk]:
    """问题 → FAISS Top-K → 按 id 回 DB 取全文。

    多取 2 倍候选再按 ready 状态过滤（文档 failed/processing 的分块不入索引，
    此处过滤为双保险）。joinedload 预加载 doc，避免 session 关闭后 lazy load。
    """
    if policy_index.size == 0:
        return []
    q_vec = await embed_text(query)
    hits = policy_index.search(q_vec, top_k * 2)  # [(chunk_id, 余弦分)]
    if not hits:
        return []
    ids = [h[0] for h in hits]
    rows = db.scalars(
        select(PolicyChunk)
        .join(PolicyDoc)
        .options(joinedload(PolicyChunk.doc))
        .where(PolicyChunk.id.in_(ids), PolicyDoc.status == "ready")
    ).all()
    by_id = {r.id: r for r in rows}
    out: list[PolicyChunk] = []
    for cid, score in hits:
        if cid in by_id and score > 0.3:  # 相似度过低直接丢弃
            out.append(by_id[cid])
        if len(out) >= top_k:
            break
    return out


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
