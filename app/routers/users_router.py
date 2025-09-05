import os
from uuid import uuid4
from typing import Any, Optional, Dict, List
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
    UploadFile,
    File,
    Request,
    Body,
    Path,
    Response,
)
from sqlalchemy.orm import Session

from .. import schemas, crud, auth, models
from ..database import get_db

router = APIRouter(prefix="/users", tags=["users"])

AVATAR_DIR = "static/avatars"
ALLOWED_TYPES = {"image/jpeg": ".jpg", "image/png": ".png", "image/webp": ".webp"}
MAX_AVATAR_SIZE = 2 * 1024 * 1024  # 2 MB

os.makedirs(AVATAR_DIR, exist_ok=True)


def _user_to_dict(user: models.User, games_count: Optional[int]) -> dict:
    gc = int(games_count or 0)
    try:
        # Compat com Pydantic v2 ou v1
        if hasattr(schemas.UserOut, "model_validate"):
            user_model = schemas.UserOut.model_validate(user)
            user_dict = user_model.model_dump()
        else:
            # Pydantic v1
            user_model = schemas.UserOut.from_orm(user)
            user_dict = user_model.dict()
    except Exception:
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

@router.post("/", response_model=schemas.UserOut, status_code=status.HTTP_201_CREATED)
def create_user(
    user_in: schemas.UserCreate,
    db: Session = Depends(get_db),
) -> Any:
    try:
        email = user_in.email
    except Exception:
        data_tmp = user_in.dict() if hasattr(user_in, "dict") else dict(user_in)
        email = data_tmp.get("email")

    if not email:
        raise HTTPException(status_code=400, detail="Email é obrigatório")

    existing = db.query(models.User).filter(models.User.email == email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email já cadastrado")

    try:
        payload = user_in.dict()
    except Exception:
        payload = dict(user_in)

    pwd = payload.pop("password", None)
    if not pwd:
        raise HTTPException(status_code=400, detail="Senha é obrigatória")
    payload["hashed_password"] = auth.get_password_hash(pwd)

    # payload.setdefault("is_active", False)

    try:
        u = models.User(**payload)
        db.add(u)
        db.commit()
        db.refresh(u)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao criar usuário") from e

    try:
        games_count = db.query(models.Game).filter(models.Game.user_id == u.id).count()
    except Exception:
        games_count = 0

    return _user_to_dict(u, games_count)


@router.get("/{user_id}", response_model=schemas.UserOut)
def get_user(
    user_id: int = Path(..., description="ID do usuário"),
    db: Session = Depends(get_db),
) -> Any:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    try:
        games_count = db.query(models.Game).filter(models.Game.user_id == user.id).count()
    except Exception:
        games_count = 0

    return _user_to_dict(user, games_count)

@router.put("/{user_id}", response_model=schemas.UserOut)
def update_user(
    user_id: int,
    user_in: schemas.UserUpdate,
    db: Session = Depends(get_db),
) -> Any:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    try:
        if hasattr(user_in, "model_dump"):
            payload = user_in.model_dump(exclude_unset=True)
        else:
            payload = user_in.dict(exclude_unset=True)
    except Exception:
        payload = dict(user_in) if not isinstance(user_in, dict) else user_in

    if "email" in payload:
        other = db.query(models.User).filter(models.User.email == payload["email"], models.User.id != user_id).first()
        if other:
            raise HTTPException(status_code=400, detail="Email já está em uso")

    if "password" in payload:
        pwd = payload.pop("password")
        if pwd:
            payload["hashed_password"] = auth.get_password_hash(pwd)

    for k, v in payload.items():
        if hasattr(user, k):
            setattr(user, k, v)

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao atualizar usuário") from e

    try:
        games_count = db.query(models.Game).filter(models.Game.user_id == user.id).count()
    except Exception:
        games_count = 0

    return _user_to_dict(user, games_count)


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_user(
    user_id: int,
    db: Session = Depends(get_db),
) -> Response:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")

    try:
        db.delete(user)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="Erro ao remover usuário") from e

    return Response(status_code=status.HTTP_204_NO_CONTENT)



@router.get("/me", response_model=schemas.UserOut)
def read_users_me(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
) -> Any:
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
) -> Any:
    updated = crud.update_user(db, current_user.id, user_in)
    if not updated:
        raise HTTPException(status_code=400, detail="Não foi possível atualizar o perfil")

    data = crud.get_user_profile(db, updated.id)
    if not data:
        raise HTTPException(
            status_code=404, detail="Usuário não encontrado após atualização"
        )

    return _user_to_dict(data["user"], data["games_count"])


@router.patch("/me", response_model=schemas.UserOut)
def patch_users_me(
    payload: Dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
) -> Any:
    # remover avatar (quando enviado como null)
    if "avatar_url" in payload and payload["avatar_url"] is None:
        try:
            old = getattr(current_user, "avatar_url", None)
            if old and old.startswith("/static/"):
                stored_path = old.lstrip("/")
                if os.path.exists(stored_path):
                    os.remove(stored_path)
        except Exception:
            pass

        if hasattr(crud, "set_user_avatar"):
            user = crud.set_user_avatar(db, current_user.id, None)
        else:
            current_user.avatar_url = None
            db.add(current_user)
            db.commit()
            db.refresh(current_user)
            user = current_user

        data = crud.get_user_profile(db, current_user.id)
        if not data:
            raise HTTPException(
                status_code=404, detail="Usuário não encontrado após remoção"
            )
        return _user_to_dict(data["user"], data["games_count"])

    updated = crud.update_user(db, current_user.id, payload)
    if not updated:
        raise HTTPException(status_code=400, detail="Não foi possível atualizar o perfil")
    data = crud.get_user_profile(db, updated.id)
    if not data:
        raise HTTPException(
            status_code=404, detail="Usuário não encontrado após atualização"
        )
    return _user_to_dict(data["user"], data["games_count"])


@router.post("/change-password")
def change_password(
    payload: schemas.ChangePassword,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
) -> Any:
    if not auth.verify_password(payload.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="Senha antiga incorreta"
        )

    hashed = auth.get_password_hash(payload.new_password)
    updated = crud.set_user_password(db, current_user.id, hashed)
    if not updated:
        raise HTTPException(status_code=500, detail="Erro ao atualizar senha")
    return {"ok": True}


def _save_avatar_file(contents: bytes, content_type: str) -> str:
    if content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=400, detail="Tipo de imagem não suportado")

    if len(contents) > MAX_AVATAR_SIZE:
        raise HTTPException(status_code=400, detail="Arquivo muito grande (máx 2MB)")

    ext = ALLOWED_TYPES[content_type]
    filename = f"{uuid4().hex}{ext}"
    os.makedirs(AVATAR_DIR, exist_ok=True)
    path = os.path.join(AVATAR_DIR, filename)

    try:
        with open(path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Falha ao salvar arquivo") from e

    return f"/{AVATAR_DIR}/{filename}"


@router.post("/me/avatar")
async def upload_avatar(
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
) -> Any:
    content_type = getattr(file, "content_type", None)
    if not content_type:
        raise HTTPException(status_code=400, detail="Tipo de conteúdo ausente")

    contents = await file.read()
    public_path = _save_avatar_file(contents, content_type)

    try:
        old = getattr(current_user, "avatar_url", None)
        if old and old.startswith("/static/"):
            stored_path = old.lstrip("/")
            if os.path.exists(stored_path):
                os.remove(stored_path)
    except Exception:
        pass

    if hasattr(crud, "set_user_avatar"):
        user = crud.set_user_avatar(db, current_user.id, public_path)
    else:
        current_user.avatar_url = public_path
        db.add(current_user)
        db.commit()
        db.refresh(current_user)
        user = current_user

    base = str(request.base_url).rstrip("/")
    full_url = f"{base}{public_path}"

    data = crud.get_user_profile(db, current_user.id)
    if not data:
        user_out = _user_to_dict(user, 0)
    else:
        user_out = _user_to_dict(data["user"], data["games_count"])

    return {"avatar_url": full_url, "user": user_out}


@router.get("/me/games")
def read_my_games(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
) -> Any:
    games = db.query(models.Game).filter(models.Game.user_id == current_user.id).all()

    out = []
    for g in games:
        out.append(
            {
                "id": g.id,
                "name": g.name,
                "external_guid": g.external_guid,
                "cover_url": g.cover_url,
                "description": g.description,
                "user_id": g.user_id,
                "status": g.status,
                "start_date": g.start_date.isoformat() if g.start_date else None,
                "finish_date": g.finish_date.isoformat() if g.finish_date else None,
                "created_at": g.created_at.isoformat() if g.created_at else None,
                "updated_at": g.updated_at.isoformat() if g.updated_at else None,
            }
        )
    return out


@router.get("/{user_id}/games")
def read_user_games(
    user_id: int = Path(..., description="ID do usuário"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
) -> Any:
    if current_user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Acesso negado"
        )

    games = db.query(models.Game).filter(models.Game.user_id == user_id).all()

    out = []
    for g in games:
        out.append(
            {
                "id": g.id,
                "name": g.name,
                "external_guid": g.external_guid,
                "cover_url": g.cover_url,
                "description": g.description,
                "user_id": g.user_id,
                "status": g.status,
                "start_date": g.start_date.isoformat() if g.start_date else None,
                "finish_date": g.finish_date.isoformat() if g.finish_date else None,
                "created_at": g.created_at.isoformat() if g.created_at else None,
                "updated_at": g.updated_at.isoformat() if g.updated_at else None,
            }
        )
    return out
