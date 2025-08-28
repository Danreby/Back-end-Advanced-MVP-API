import os
import uuid
from pathlib import Path
from typing import Tuple, Optional
from fastapi import UploadFile

UPLOAD_DIR = Path("static/uploads/avatars")
MEDIA_URL_PREFIX = "/static/uploads/avatars"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

def _secure_ext(filename: str) -> str:
    name = filename or ""
    _, ext = os.path.splitext(name)
    ext = ext.lower()
    if ext not in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        ext = ".png"
    return ext

def save_avatar_file(file: UploadFile, user_id: int) -> Tuple[str, Path]:
    ext = _secure_ext(file.filename)
    filename = f"{user_id}-{uuid.uuid4().hex}{ext}"
    dest = UPLOAD_DIR / filename

    with dest.open("wb") as f:
        while True:
            chunk = file.file.read(1024 * 64)
            if not chunk:
                break
            f.write(chunk)
    try:
        file.file.close()
    except Exception:
        pass

    url = f"{MEDIA_URL_PREFIX}/{filename}"
    return url, dest

def remove_local_file_from_url(avatar_url: Optional[str]) -> bool:
    if not avatar_url:
        return False
    if not avatar_url.startswith(MEDIA_URL_PREFIX):
        return False
    filename = avatar_url.split(MEDIA_URL_PREFIX, 1)[-1].lstrip("/")
    path = UPLOAD_DIR / filename
    try:
        if path.exists():
            path.unlink()
            return True
    except Exception:
        pass
    return False
