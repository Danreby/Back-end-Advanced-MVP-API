import os
from uuid import uuid4
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Request
from sqlalchemy.orm import Session

from .. import schemas, crud, auth, models
from ..database import get_db

router = APIRouter(prefix="/users", tags=["users"])

AVATAR_DIR = "static/avatars"
ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2 MB


@router.get("/me", response_model=schemas.UserOut)
def read_users_me(current_user: models.User = Depends(auth.get_current_user)):
    """
    Retorna o usuário autenticado.
    """
    return current_user


@router.put("/me", response_model=schemas.UserOut)
def update_users_me(
    user_in: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Atualiza campos permitidos do usuário atual (name, bio, avatar_url opcional).
    """
    updated = crud.update_user(db, current_user.id, user_in)
    if not updated:
        raise HTTPException(status_code=400, detail="Não foi possível atualizar o perfil")
    return updated


@router.post("/change-password")
def change_password(
    payload: schemas.ChangePassword,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
) -> Any:
    """
    Altera a senha do usuário atual após validação da senha antiga.
    """
    if not auth.verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Senha antiga incorreta")

    hashed = auth.get_password_hash(payload.new_password)
    updated = crud.set_user_password(db, current_user.id, hashed)
    if not updated:
        raise HTTPException(status_code=500, detail="Erro ao atualizar senha")
    return {"ok": True}


def _save_avatar_file(contents: bytes, content_type: str) -> str:
    """
    Salva o conteúdo do avatar no disco e retorna o caminho público relativo (/static/avatars/xxxx.ext).
    Lance HTTPException em caso de erro de validação.
    """
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de imagem não suportado")

    if len(contents) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=400, detail="Arquivo muito grande (máx 2MB)")

    ext = ALLOWED_TYPES[content_type]
    filename = f"{uuid4().hex}{ext}"
    os.makedirs(AVATAR_DIR, exist_ok=True)
    path = os.path.join(AVATAR_DIR, filename)

    with open(path, "wb") as f:
        f.write(contents)

    return f"/{AVATAR_DIR}/{filename}"


@router.post("/me/avatar")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
) -> Any:
    """
    Faz upload de um avatar para o usuário autenticado.
    - Valida tipo e tamanho
    - Remove arquivo antigo se existir
    - Salva caminho relativo no banco (ex: /static/avatars/uuid.png)
    Retorna a URL pública completa do avatar no campo `avatar_url`.
    """
    contents = await file.read()
    public_path = _save_avatar_file(contents, file.content_type)

    if current_user.avatar_url:
        try:
            stored_path = current_user.avatar_url.lstrip("/")
            if os.path.exists(stored_path):
                os.remove(stored_path)
        except Exception:
            pass

    current_user.avatar_url = public_path
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    base = str(request.base_url).rstrip("/")
    full_url = f"{base}{public_path}"

    return {"avatar_url": full_url, "user": schemas.UserOut.model_validate(current_user)}
