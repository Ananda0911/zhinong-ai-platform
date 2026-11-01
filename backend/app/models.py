"""ORM 表定义（共 8 张表，详见设计文档第 5 章）。

时间统一存 UTC 字符串（ISO 格式），SQLite 无原生时区类型。
"""
from datetime import datetime, timezone

from sqlalchemy import BLOB, Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def now_str() -> str:
    return datetime.now(timezone.utc).isoformat()


# ─────────────────────────── 5.1 users ───────────────────────────
class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(Text, unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    nickname: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    role: Mapped[str] = mapped_column(Text, nullable=False)  # farmer / buyer / admin
    region: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[str] = mapped_column(Text, default=now_str)


# ─────────────────────── 5.2 supply_infos ────────────────────────
class SupplyInfo(Base):
    __tablename__ = "supply_infos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False, index=True)  # 粮油/果蔬/畜禽/水产/中药材/其他
    variety: Mapped[str | None] = mapped_column(Text)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(Text, nullable=False)
    price: Mapped[float | None] = mapped_column(Float)  # None = 面议
    region: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    images: Mapped[str | None] = mapped_column(Text)   # JSON 数组字符串
    embedding: Mapped[bytes | None] = mapped_column(BLOB)
    status: Mapped[str] = mapped_column(Text, default="active", index=True)  # active/offline/expired
    expire_at: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, default=now_str)
    updated_at: Mapped[str] = mapped_column(Text, default=now_str, onupdate=now_str)

    user: Mapped[User] = relationship()


# ────────────────────── 5.3 purchase_infos ───────────────────────
class PurchaseInfo(Base):
    __tablename__ = "purchase_infos"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    quantity: Mapped[float] = mapped_column(Float, nullable=False)
    unit: Mapped[str] = mapped_column(Text, nullable=False)
    target_region: Mapped[str | None] = mapped_column(Text)  # 意向产区，空=不限
    budget: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    embedding: Mapped[bytes | None] = mapped_column(BLOB)
    status: Mapped[str] = mapped_column(Text, default="active", index=True)  # active/closed/expired
    expire_at: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, default=now_str)
    updated_at: Mapped[str] = mapped_column(Text, default=now_str, onupdate=now_str)

    user: Mapped[User] = relationship()


# ─────────────────── 5.4 chat_sessions 会话 ──────────────────────
class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(Text, nullable=False)  # agritech / policy
    title: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, default=now_str)
    updated_at: Mapped[str] = mapped_column(Text, default=now_str, onupdate=now_str)

    messages: Mapped[list["ChatMessage"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


# ─────────────────── 5.5 chat_messages 消息 ───────────────────────
class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("chat_sessions.id"), nullable=False, index=True)
    role: Mapped[str] = mapped_column(Text, nullable=False)  # user / assistant
    content: Mapped[str] = mapped_column(Text, nullable=False)
    image_url: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[str] = mapped_column(Text, default=now_str)

    session: Mapped[ChatSession] = relationship(back_populates="messages")


# ─────────────────── 5.6 policy_docs 政策文档 ─────────────────────
class PolicyDoc(Base):
    __tablename__ = "policy_docs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    file_name: Mapped[str | None] = mapped_column(Text)
    file_path: Mapped[str | None] = mapped_column(Text)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(Text, default="processing")  # processing/ready/failed
    error_msg: Mapped[str | None] = mapped_column(Text)  # 解析失败原因
    created_at: Mapped[str] = mapped_column(Text, default=now_str)

    chunks: Mapped[list["PolicyChunk"]] = relationship(
        back_populates="doc", cascade="all, delete-orphan"
    )


# ─────────────────── 5.7 policy_chunks 政策分块 ───────────────────
class PolicyChunk(Base):
    __tablename__ = "policy_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    doc_id: Mapped[int] = mapped_column(ForeignKey("policy_docs.id"), nullable=False, index=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[bytes | None] = mapped_column(BLOB)

    doc: Mapped[PolicyDoc] = relationship(back_populates="chunks")


# ─────────────── 5.8 marketing_records 文案生成记录 ───────────────
class MarketingRecord(Base):
    __tablename__ = "marketing_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    gen_type: Mapped[str] = mapped_column(Text, nullable=False)  # detail / live / video
    input_json: Mapped[str | None] = mapped_column(Text)
    result: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[str] = mapped_column(Text, default=now_str)
