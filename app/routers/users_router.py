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


def _user_to_dict(user: models.User, games_count: Optional[int]) -> dict:
    """
    Converte um ORM User para dict compatível com schemas.UserOut e injeta games_count.
    Suporta Pydantic v2 (model_validate/model_dump) e v1 (from_orm/dict).
    """
    gc = int(games_count or 0)
    try:
        # Pydantic v2
        if hasattr(schemas.UserOut, "model_validate"):
            user_model = schemas.UserOut.model_validate(user)
            user_dict = user_model.model_dump()
        else:
            # Pydantic v1
            user_model = schemas.UserOut.from_orm(user)
            user_dict = user_model.dict()
    except Exception:
        # Fallback: construir dict básico a partir dos atributos do ORM
        user_dict = {
            "id": getattr(user, "id", None),
            "email": getattr(user, "email", None),
            "name": getattr(user, "name", None),
            "bio": getattr(user, "bio", None),
            "avatar_url": getattr(user, "avatar_url", None),
            "is_active": getattr(user, "is_active", True),
            "created_at": getattr(user, "created_at", None),
        }

    user_dict["games_count"] = gc
    return user_dict


@router.get("/me", response_model=schemas.UserOut)
def read_users_me(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Retorna o usuário autenticado com games_count.
    """
    data = crud.get_user_profile(db, current_user.id)
    if not data:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    user = data["user"]
    games_count = data["games_count"]
    return _user_to_dict(user, games_count)


@router.put("/me", response_model=schemas.UserOut)
def update_users_me(
    user_in: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Atualiza campos permitidos do usuário atual (name, bio, avatar_url opcional).
    Retorna o usuário atualizado com games_count.
    """
    updated = crud.update_user(db, current_user.id, user_in)
    if not updated:
        raise HTTPException(status_code=400, detail="Não foi possível atualizar o perfil")

    data = crud.get_user_profile(db, updated.id)
    if not data:
        raise HTTPException(status_code=404, detail="Usuário não encontrado após atualização")

    return _user_to_dict(data["user"], data["games_count"])


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
    Lança HTTPException em caso de erro de validação.
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
    Retorna a URL pública completa do avatar no campo `avatar_url` e o usuário atualizado
    (incluindo games_count) no campo `user`.
    """
    contents = await file.read()
    public_path = _save_avatar_file(contents, file.content_type)

    # remove arquivo antigo se existir
    if current_user.avatar_url:
        try:
            stored_path = current_user.avatar_url.lstrip("/")
            if os.path.exists(stored_path):
                os.remove(stored_path)
        except Exception:
            pass

    # atualiza e persiste
    current_user.avatar_url = public_path
    db.add(current_user)
    db.commit()
    db.refresh(current_user)

    # monta url pública completa
    base = str(request.base_url).rstrip("/")
    full_url = f"{base}{public_path}"

    # busca games_count atualizado e monta resposta
    data = crud.get_user_profile(db, current_user.id)
    if not data:
        # fallback: apenas retorna usuário sem games_count (não deveria acontecer)
        user_out = _user_to_dict(current_user, 0)
    else:
        user_out = _user_to_dict(data["user"], data["games_count"])

    return {"avatar_url": full_url, "user": user_out}
