"""政策文档解析：PDF 走 MinerU 官方 API（精准解析），docx/txt/md 直读。

MinerU API 流程（https://mineru.net）：
  1. POST /api/v4/file-urls/batch  申请上传链接 → {batch_id, file_urls}
  2. PUT 文件到上传链接（无 Content-Type），系统自动提交解析任务
  3. GET /api/v4/extract-results/batch/{batch_id} 轮询 → state=done → full_zip_url
  4. 下载 zip → 解压取 full.md（Markdown 解析结果，表格为 HTML 形式）
"""
import asyncio
import io
import re
import zipfile
from html.parser import HTMLParser
from pathlib import Path

import httpx

from app.config import settings

MINERU_BASE = "https://mineru.net"
POLL_INTERVAL = 5  # 轮询间隔（秒）
POLL_TIMEOUT = 600  # 最长等待 10 分钟

ALLOWED_EXTS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB


class MineruError(Exception):
    """解析失败（信息会写入 policy_docs 状态，前端可见）。"""


# ─────────────────────── 表格 HTML 线性化 ───────────────────────
class _TableParser(HTMLParser):
    """提取 <table> 的行列文本，转成"表头：值"纯文本（利于 embedding）。"""

    def __init__(self):
        super().__init__()
        self.rows: list[list[str]] = []
        self._cur_row: list[str] | None = None
        self._cur_cell: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag == "tr":
            self._cur_row = []
        elif tag in ("td", "th"):
            self._cur_cell = []

    def handle_data(self, data):
        if self._cur_row is not None and self._cur_cell is not None:
            self._cur_cell.append(data)

    def handle_endtag(self, tag):
        if tag in ("td", "th") and self._cur_row is not None:
            text = "".join(self._cur_cell).strip()
            self._cur_row.append(text)
            self._cur_cell = None
        elif tag == "tr" and self._cur_row is not None:
            if any(c for c in self._cur_row):
                self.rows.append(self._cur_row)
            self._cur_row = None


def _linearize_table(html: str) -> str:
    """表格 HTML → "字段：值" 纯文本。首行为表头，其余行逐行拼接。"""
    parser = _TableParser()
    parser.feed(html)
    if not parser.rows:
        return ""
    header = parser.rows[0]
    lines = []
    for row in parser.rows[1:]:
        pairs = []
        for i, cell in enumerate(row):
            key = header[i] if i < len(header) and header[i] else f"第{i + 1}项"
            if cell:
                pairs.append(f"{key}：{cell}")
        if pairs:
            lines.append("；".join(pairs))
    return "\n".join(lines)


def linearize_tables(markdown: str) -> str:
    """把 Markdown 中的 <table> HTML 替换为线性化纯文本（分块前调用）。"""

    def _repl(m):
        text = _linearize_table(m.group(0))
        return text if text else m.group(0)

    return re.sub(r"<table[^>]*>.*?</table>", _repl, markdown, flags=re.S | re.I)


# ─────────────────────── 直读格式（docx/txt/md） ───────────────────────
def _read_docx(path: Path) -> str:
    from docx import Document  # 延迟导入，加快启动

    doc = Document(str(path))
    parts = [p.text for p in doc.paragraphs if p.text.strip()]
    for table in doc.tables:  # docx 表格同样线性化
        rows = [[c.text.strip() for c in r.cells] for r in table.rows]
        if rows:
            header = rows[0]
            for row in rows[1:]:
                pairs = [
                    f"{header[i]}：{cell}"
                    for i, cell in enumerate(row)
                    if cell and (i < len(header) and header[i])
                ]
                if pairs:
                    parts.append("；".join(pairs))
    return "\n".join(parts)


def _read_plain(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


# ─────────────────────── MinerU API（PDF） ───────────────────────
async def _parse_pdf_via_api(path: Path, file_name: str) -> str:
    if settings.MINERU_MODE != "api":
        raise MineruError("仅支持 MinerU API 模式（MINERU_MODE=api）")
    if not settings.MINERU_API_TOKEN:
        raise MineruError("未配置 MINERU_API_TOKEN，无法解析 PDF（请在 mineru.net 申请）")

    headers = {"Authorization": f"Bearer {settings.MINERU_API_TOKEN}"}
    async with httpx.AsyncClient(timeout=60) as client:
        # 1. 申请上传链接
        resp = await client.post(
            f"{MINERU_BASE}/api/v4/file-urls/batch",
            headers=headers,
            json={
                "files": [{"name": file_name, "is_ocr": True}],
                "model_version": settings.MINERU_MODEL_VERSION,
                "language": "ch",
                "enable_table": True,
            },
        )
        data = _check(resp, "申请上传链接失败")
        batch_id = data["batch_id"]
        upload_url = data["file_urls"][0]

        # 2. PUT 上传文件（不能带 Content-Type）
        put = await client.put(upload_url, content=path.read_bytes())
        if put.status_code != 200:
            raise MineruError(f"文件上传失败（HTTP {put.status_code}）")

        # 3. 轮询解析结果
        waited = 0
        while True:
            resp = await client.get(
                f"{MINERU_BASE}/api/v4/extract-results/batch/{batch_id}", headers=headers
            )
            data = _check(resp, "查询解析结果失败")
            result = data["extract_result"][0]
            state = result.get("state")
            if state == "done":
                zip_url = result["full_zip_url"]
                break
            if state == "failed":
                raise MineruError(f"MinerU 解析失败：{result.get('err_msg') or '未知原因'}")
            if waited >= POLL_TIMEOUT:
                raise MineruError("解析超时（超过 10 分钟），请稍后重试或重新上传")
            await asyncio.sleep(POLL_INTERVAL)
            waited += POLL_INTERVAL

        # 4. 下载 zip → 解压取 full.md
        zip_resp = await client.get(zip_url)
        if zip_resp.status_code != 200:
            raise MineruError(f"下载解析结果失败（HTTP {zip_resp.status_code}）")
        with zipfile.ZipFile(io.BytesIO(zip_resp.content)) as zf:
            md_names = [n for n in zf.namelist() if n.endswith("full.md")]
            if not md_names:
                raise MineruError("解析结果中未找到 Markdown 文件")
            md = zf.read(md_names[0]).decode("utf-8", errors="ignore")

    # 相对图片链接无意义（未下载图片），去掉 markdown 图片引用
    return re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)


def _check(resp: httpx.Response, action: str) -> dict:
    """校验 MinerU 响应，返回 data 字段。"""
    if resp.status_code != 200:
        raise MineruError(f"{action}（HTTP {resp.status_code}）")
    body = resp.json()
    if body.get("code") != 0:
        raise MineruError(f"{action}：{body.get('msg') or body}")
    return body["data"]


# ─────────────────────── 统一入口 ───────────────────────
async def parse_document(path: Path) -> str:
    """解析政策文档为 Markdown 文本（含表格线性化）。

    pdf → MinerU API；docx/txt/md → 本地直读。
    """
    ext = path.suffix.lower()
    if ext == ".pdf":
        md = await _parse_pdf_via_api(path, path.name)
    elif ext == ".docx":
        md = _read_docx(path)
    elif ext in (".txt", ".md"):
        md = _read_plain(path)
    else:
        raise MineruError(f"不支持的文件类型：{ext}（支持 pdf/docx/txt/md）")

    md = linearize_tables(md)
    if not md.strip():
        raise MineruError("解析结果为空，请检查文档内容")
    return md
