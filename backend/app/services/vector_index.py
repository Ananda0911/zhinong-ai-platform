"""FAISS 向量索引封装：IndexIDMap2(IndexFlatIP)。

设计要点：
- 归一化后做内积（IP）= 余弦相似度（FAISS 标准做法）
- IndexIDMap2 支持 add_with_ids / remove_ids，id 直接用数据库主键
- 索引只负责"存在性"：品类/状态/过期等元数据过滤在 DB 层做，
  因此上下架、惰性过期均无需同步索引，仅新增/删除时同步
- 进程内存索引：启动时从 SQLite 全量构建（当前量级毫秒级）；
  注意 uvicorn 需单进程（workers=1），多 worker 需改为独立检索服务
"""
import threading

import faiss
import numpy as np


def _normalize(vec: np.ndarray) -> np.ndarray:
    n = np.linalg.norm(vec)
    return vec / n if n > 0 else vec


class VectorIndex:
    """线程安全的 FAISS 余弦索引（维度在首次写入时自动确定）。"""

    def __init__(self):
        self._index = None  # 惰性创建（维度未知前不建）
        self._lock = threading.Lock()

    @property
    def size(self) -> int:
        return 0 if self._index is None else self._index.ntotal

    def _ensure(self, dim: int):
        if self._index is None:
            self._index = faiss.IndexIDMap2(faiss.IndexFlatIP(dim))

    def add(self, _id: int, blob: bytes) -> None:
        vec = np.frombuffer(blob, dtype=np.float32)
        with self._lock:
            self._ensure(vec.shape[0])
            self._index.add_with_ids(
                _normalize(vec).reshape(1, -1), np.array([_id], dtype=np.int64)
            )

    def remove_many(self, ids: list[int]) -> None:
        if not ids or self._index is None:
            return
        with self._lock:
            self._index.remove_ids(np.array(ids, dtype=np.int64))

    def search(self, blob: bytes, top_k: int) -> list[tuple[int, float]]:
        """查询向量（bytes）→ [(id, 余弦分数)] 降序。"""
        if self._index is None or self._index.ntotal == 0:
            return []
        q = _normalize(np.frombuffer(blob, dtype=np.float32)).reshape(1, -1)
        with self._lock:
            scores, ids = self._index.search(q, min(top_k, self._index.ntotal))
        return [(int(i), float(s)) for i, s in zip(ids[0], scores[0]) if i != -1]

    def rebuild(self, items: list[tuple[int, bytes]]) -> None:
        """全量重建：items = [(id, embedding_bytes)]。"""
        with self._lock:
            self._index = None
            if not items:
                return
            mat = np.vstack(
                [_normalize(np.frombuffer(b, dtype=np.float32)) for _, b in items]
            )
            idx = faiss.IndexIDMap2(faiss.IndexFlatIP(mat.shape[1]))
            idx.add_with_ids(mat, np.array([i for i, _ in items], dtype=np.int64))
            self._index = idx
