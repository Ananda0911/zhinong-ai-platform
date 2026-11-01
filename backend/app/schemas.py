"""Pydantic 请求/响应模型。"""
from datetime import datetime

from pydantic import BaseModel, Field


# ───────────────────────── 认证 ─────────────────────────
class RegisterIn(BaseModel):
    username: str = Field(min_length=3, max_length=32, pattern=r"^[a-zA-Z0-9_]+$")
    password: str = Field(min_length=6, max_length=64)
    nickname: str = Field(min_length=1, max_length=32)
    role: str = Field(pattern=r"^(farmer|buyer)$")  # admin 不开放注册
    region: str | None = Field(default=None, max_length=64)
    phone: str | None = Field(default=None, max_length=20)


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    id: int
    username: str
    nickname: str | None
    phone: str | None
    role: str
    region: str | None
    is_active: int
    created_at: str

    model_config = {"from_attributes": True}


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ───────────────────────── 会话/消息 ─────────────────────────
class SessionCreate(BaseModel):
    type: str = Field(pattern=r"^(agritech|policy)$")


class SessionOut(BaseModel):
    id: int
    type: str
    title: str | None
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class MessageOut(BaseModel):
    id: int
    session_id: int
    role: str
    content: str
    image_url: str | None
    created_at: str

    model_config = {"from_attributes": True}


class AgritechChatIn(BaseModel):
    session_id: int
    content: str = Field(min_length=1, max_length=2000)
    image_url: str | None = None


class PolicyChatIn(BaseModel):
    session_id: int
    content: str = Field(min_length=1, max_length=2000)


# ───────────────────── 管理后台 ─────────────────────
class AdminUserStatusIn(BaseModel):
    is_active: bool


class AdminContentStatusIn(BaseModel):
    status: str = Field(pattern=r"^(active|offline|closed)$")


# ───────────────────── 营销工具 ─────────────────────
CATEGORIES = ("粮油", "果蔬", "畜禽", "水产", "中药材", "其他")

CATEGORY_PATTERN = r"^(粮油|果蔬|畜禽|水产|中药材|其他)$"


class MarketingGenerateIn(BaseModel):
    product_name: str = Field(min_length=1, max_length=50)
    category: str = Field(pattern=CATEGORY_PATTERN)
    features: str | None = Field(default=None, max_length=1000)
    selling_points: str | None = Field(default=None, max_length=1000)
    gen_type: str = Field(pattern=r"^(detail|live|video)$")
    tone: str | None = Field(default=None, max_length=100)


# ───────────────────── 产销对接 ─────────────────────


class SupplyCreate(BaseModel):
    title: str = Field(min_length=2, max_length=50)
    category: str = Field(pattern=CATEGORY_PATTERN)
    variety: str | None = Field(default=None, max_length=30)
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=10)
    price: float | None = Field(default=None, ge=0)
    region: str = Field(min_length=2, max_length=50)
    description: str | None = Field(default=None, max_length=2000)
    images: list[str] = Field(default=[], max_length=6)
    expire_days: int = Field(default=30, ge=1, le=365)


class PurchaseCreate(BaseModel):
    title: str = Field(min_length=2, max_length=50)
    category: str = Field(pattern=CATEGORY_PATTERN)
    quantity: float = Field(gt=0)
    unit: str = Field(min_length=1, max_length=10)
    target_region: str | None = Field(default=None, max_length=50)
    budget: str | None = Field(default=None, max_length=50)
    description: str | None = Field(default=None, max_length=2000)
    expire_days: int = Field(default=30, ge=1, le=365)


class StatusUpdate(BaseModel):
    status: str = Field(pattern=r"^(active|offline|closed)$")
