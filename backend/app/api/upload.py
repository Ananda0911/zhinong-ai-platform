"""通用图片上传（multipart，≤2MB，jpg/png/webp）。"""
import time
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import JSONResponse

from app.deps import get_current_user

router = APIRouter(prefix="/api/upload", tags=["upload"])

ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_SIZE = 2 * 1024 * 1024  # 2MB


@router.post("/image")
async def upload_image(file: UploadFile = File(...), user=Depends(get_current_user)):
    ext = ALLOWED_TYPES.get(file.content_type)
    if ext is None:
        raise HTTPException(400, "仅支持 jpg / png / webp 图片")

    data = await file.read()
    if len(data) > MAX_SIZE:
        raise HTTPException(400, "图片不能超过 2MB")

    # uploads/images/yyyyMMdd_uuid.ext
    save_dir = Path("uploads") / "images"
    save_dir.mkdir(parents=True, exist_ok=True)
    name = f"{time.strftime('%Y%m%d')}_{uuid.uuid4().hex[:12]}{ext}"
    (save_dir / name).write_bytes(data)

    return JSONResponse({"url": f"/uploads/images/{name}"})
