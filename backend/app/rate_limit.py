"""slowapi 限流器：按用户（Authorization 头）分桶，未登录退回 IP。"""
import hashlib

from fastapi import Request
from slowapi import Limiter
from slowapi.util import get_remote_address


def _user_or_ip_key(request: Request) -> str:
    """同一 token 同一桶（等价同一用户），无 token（未登录）按 IP。

    token 只记 hash 前缀：限流 key 稳定性要求同 token 同桶即可，
    避免完整凭证落入日志（日志泄露 ≠ 会话泄露）。
    """
    auth_header = request.headers.get("authorization")
    if not auth_header:
        return f"ip:{get_remote_address(request)}"
    digest = hashlib.sha256(auth_header.encode()).hexdigest()[:12]
    return f"token:{digest}"


limiter = Limiter(key_func=_user_or_ip_key)
