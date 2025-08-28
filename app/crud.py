# app/crud.py
from datetime import datetime
from typing import List, Optional, Any, Union, Dict

from sqlalchemy.orm import Session
from sqlalchemy import func

from . import models, schemas
from app.auth import hash_token, token_expiration
from pathlib import Path

# --- Users ---
def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user: schemas.UserCreate, hashed_password: str, is_active: bool = False) -> models.User:
    db_user = models.User(
        email=user.email,
        name=user.name,
        hashed_password=hashed_password,
        is_active=is_active,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user


def activate_user_by_email(db: Session, email: str) -> Optional[models.User]:
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return None
    user.is_active = True
    user.updated_at = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_profile(db: Session, user_id: int) -> Optional[Dict[str, Any]]:
    """
    Retorna {"user": User, "games_count": int} ou None
    """
    res = (
        db.query(models.User, func.count(models.Game.id).label("games_count"))
          .outerjoin(models.Game, models.Game.user_id == models.User.id)
          .filter(models.User.id == user_id)
          .group_by(models.User.id)
          .first()
    )
    if not res:
        return None
    user, games_count = res
    return {"user": user, "games_count": int(games_count)}


def update_user(db: Session, user_id: int, user_in: Union[schemas.UserUpdate, Dict[str, Any]]) -> Optional[models.User]:
    """
    Atualiza somente campos permitidos enviados em user_in.
    Suporta Pydantic v2 (model_dump) e v1 (dict) e dict cru.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None

    data: Dict[str, Any] = {}
    try:
        if hasattr(user_in, "model_dump"):
            data = user_in.model_dump(exclude_unset=True) or {}
        elif hasattr(user_in, "dict"):
            data = user_in.dict(exclude_unset=True) or {}
        elif isinstance(user_in, dict):
            data = user_in
    except Exception:
        if isinstance(user_in, dict):
            data = user_in

    allowed = {"name", "bio"}  # campos permitidos para atualização aqui
    for k, v in data.items():
        if k in allowed:
            setattr(user, k, v)

    user.updated_at = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_user_password(db: Session, user_id: int, hashed_password: str) -> bool:
    """
    Atualiza a senha (usa o hash já gerado).
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return False
    user.hashed_password = hashed_password
    user.updated_at = datetime.utcnow()
    db.add(user)
    db.commit()
    return True


# --- Games ---
def create_game(db: Session, user_id: int, game_in) -> models.Game:
    g = models.Game(
        name=game_in.name,
        external_guid=game_in.external_guid,
        cover_url=game_in.cover_url,
        description=game_in.description,
        status=game_in.status or "Wishlist",
        start_date=game_in.start_date,
        finish_date=game_in.finish_date,
        user_id=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    return g


def get_game(db: Session, game_id: int) -> Optional[models.Game]:
    return db.query(models.Game).filter(models.Game.id == game_id).first()


def get_games_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 50) -> List[models.Game]:
    return db.query(models.Game).filter(models.Game.user_id == user_id).offset(skip).limit(limit).all()


def delete_game(db: Session, game: models.Game) -> None:
    db.delete(game)
    db.commit()


def update_game(db: Session, game: models.Game, data: Dict[str, Any]) -> models.Game:
    for k, v in data.items():
        if v is not None:
            setattr(game, k, v)
    game.updated_at = datetime.utcnow()
    db.add(game)
    db.commit()
    db.refresh(game)
    return game


# --- Reviews ----
def create_review(db: Session, user_id: int, game_id: int, review_in) -> Optional[models.Review]:
    existing = db.query(models.Review).filter(models.Review.user_id == user_id, models.Review.game_id == game_id).first()
    if existing:
        return None
    r = models.Review(
        user_id=user_id,
        game_id=game_id,
        rating=review_in.rating,
        review_text=review_in.review_text,
        is_public=review_in.is_public if review_in.is_public is not None else True,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


def get_review(db: Session, review_id: int) -> Optional[models.Review]:
    return db.query(models.Review).filter(models.Review.id == review_id).first()


def update_review(db: Session, review: models.Review, data: Dict[str, Any]) -> models.Review:
    for k, v in data.items():
        if v is not None:
            setattr(review, k, v)
    review.updated_at = datetime.utcnow()
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


def delete_review(db: Session, review: models.Review) -> None:
    db.delete(review)
    db.commit()


def get_reviews_by_game(db: Session, game_id: int, public_only: bool = True, skip: int = 0, limit: int = 50):
    q = db.query(models.Review).filter(models.Review.game_id == game_id)
    if public_only:
        q = q.filter(models.Review.is_public == True)
    total = q.count()
    items = q.offset(skip).limit(limit).all()
    return total, items


# --- avatar ---
def set_user_avatar(db: Session, user_id: int, avatar_url: Optional[str]) -> Optional[models.User]:
    """
    Define o avatar_url (path relativo, ex: '/static/avatars/uuid.png') para o usuário.
    Retorna o user atualizado.
    """
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    user.avatar_url = avatar_url
    user.updated_at = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_avatar_url(db: Session, user_id: int) -> Optional[str]:
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        return None
    return user.avatar_url


# --- Remember token ---
def create_remember_token(db: Session, user: models.User, raw_token: str, expires_at=None,
                          user_agent: Optional[str] = None, ip: Optional[str] = None) -> models.RememberToken:
    token_hash = hash_token(raw_token)
    if expires_at is None:
        expires_at = token_expiration(days=30)
    obj = models.RememberToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=expires_at,
        user_agent=user_agent,
        ip=ip,
        created_at=datetime.utcnow()
    )
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def get_remember_token_by_raw(db: Session, raw_token: str) -> Optional[models.RememberToken]:
    token_hash = hash_token(raw_token)
    return db.query(models.RememberToken).filter_by(token_hash=token_hash).first()


def revoke_remember_token(db: Session, token_obj: models.RememberToken) -> None:
    if token_obj:
        db.delete(token_obj)
        db.commit()


def revoke_all_user_tokens(db: Session, user: models.User) -> None:
    db.query(models.RememberToken).filter_by(user_id=user.id).delete()
    db.commit()
