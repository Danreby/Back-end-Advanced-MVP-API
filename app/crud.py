from datetime import datetime
from typing import List, Optional, Any, Union, Dict

from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_, and_

from . import models, schemas
from app.utils.security import hash_token, token_expiration
from pathlib import Path

# --- Users ---
def get_user_by_email(db: Session, email: str) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.email == email).first()


def get_user_by_id(db: Session, user_id: int) -> Optional[models.User]:
    return db.query(models.User).filter(models.User.id == user_id).first()


def create_user(db: Session, user: schemas.UserCreate, hashed_password: str, is_active: bool = False) -> models.User:
    db_user = models.User(
        email=user.email,
        name=getattr(user, "name", None),
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


def activate_user(db: Session, user: models.User) -> Optional[models.User]:
    """
    Activa um usuário (útil na rota /auth/confirm).
    """
    if not user:
        return None
    user.is_active = True
    user.updated_at = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_profile(db: Session, user_id: int) -> Optional[Dict[str, Any]]:
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

    allowed = {"name", "bio", "avatar_url"}
    for k, v in data.items():
        if k in allowed:
            setattr(user, k, v)

    user.updated_at = datetime.utcnow()
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def set_user_password(db: Session, user_id: int, hashed_password: str) -> bool:
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


# --- UserGames (sessions/pivô) ---
def create_user_game(db: Session, user_id: int, game_id: int, started_at: Optional[datetime] = None,
                     finished_at: Optional[datetime] = None) -> models.UserGame:
    ug = models.UserGame(
        user_id=user_id,
        game_id=game_id,
        started_at=started_at,
        finished_at=finished_at,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(ug)
    db.commit()
    db.refresh(ug)
    return ug


def get_user_game(db: Session, user_game_id: int) -> Optional[models.UserGame]:
    return db.query(models.UserGame).filter(models.UserGame.id == user_game_id).first()


def update_user_game(db: Session, user_game: models.UserGame, data: Dict[str, Any]) -> models.UserGame:
    for k, v in data.items():
        if hasattr(user_game, k) and v is not None:
            setattr(user_game, k, v)
    user_game.updated_at = datetime.utcnow()
    db.add(user_game)
    db.commit()
    db.refresh(user_game)
    return user_game


def delete_user_game(db: Session, user_game: models.UserGame) -> None:
    db.delete(user_game)
    db.commit()


def get_user_games_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 50) -> List[models.UserGame]:
    return db.query(models.UserGame).filter(models.UserGame.user_id == user_id).offset(skip).limit(limit).all()


def get_user_games_by_game(db: Session, game_id: int, skip: int = 0, limit: int = 100) -> List[models.UserGame]:
    return db.query(models.UserGame).filter(models.UserGame.game_id == game_id).offset(skip).limit(limit).all()


def find_coplayers_for_user_game(db: Session, user_game_id: int) -> List[models.User]:
    """
    Dado um user_game_id (uma sessão), retorna usuários que jogaram o MESMO game e cuja sessão
    se sobrepõe com a sessão de referência.
    Condição de overlap considera NULL finished_at como 'aberto' (overlap).
    """
    ref = db.query(models.UserGame).filter(models.UserGame.id == user_game_id).first()
    if not ref:
        return []

    q = db.query(models.UserGame).filter(
        models.UserGame.game_id == ref.game_id,
        models.UserGame.user_id != ref.user_id
    )

    overlap_cond = and_(
        or_(
            models.UserGame.finished_at == None,
            ref.started_at == None,
            models.UserGame.finished_at >= ref.started_at
        ),
        or_(
            ref.finished_at == None,
            models.UserGame.started_at == None,
            models.UserGame.started_at <= ref.finished_at
        )
    )

    q = q.filter(overlap_cond)

    user_game_rows = q.all()
    user_ids = {ug.user_id for ug in user_game_rows}
    if not user_ids:
        return []

    users = db.query(models.User).filter(models.User.id.in_(list(user_ids))).all()
    return users


# --- Friendships (pedidos/aceitação) ---
def get_friendship_between(db: Session, user_id: int, other_id: int) -> Optional[models.Friendship]:
    return db.query(models.Friendship).filter_by(user_id=user_id, friend_id=other_id).first()


def create_friend_request(db: Session, user_id: int, friend_id: int, message: Optional[str] = None) -> Optional[models.Friendship]:
    if user_id == friend_id:
        return None

    blocked = db.query(models.Friendship).filter(
        or_(
            and_(models.Friendship.user_id == user_id, models.Friendship.friend_id == friend_id, models.Friendship.status == "blocked"),
            and_(models.Friendship.user_id == friend_id, models.Friendship.friend_id == user_id, models.Friendship.status == "blocked"),
        )
    ).first()
    if blocked:
        return None

    existing = db.query(models.Friendship).filter_by(user_id=user_id, friend_id=friend_id).first()
    if existing:
        return None

    reverse = db.query(models.Friendship).filter_by(user_id=friend_id, friend_id=user_id).first()
    if reverse:
        if reverse.status == "pending":
            reverse.status = "accepted"
            reverse.accepted_at = datetime.utcnow()
            reverse.updated_at = datetime.utcnow()
            f = models.Friendship(
                user_id=user_id,
                friend_id=friend_id,
                status="accepted",
                message=message,
                created_at=datetime.utcnow(),
                accepted_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            db.add(f)
            db.add(reverse)
            db.commit()
            db.refresh(f)
            return f
        return None

    f = models.Friendship(
        user_id=user_id,
        friend_id=friend_id,
        status="pending",
        message=message,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(f)
    db.commit()
    db.refresh(f)
    return f


def get_friend_request(db: Session, request_id: int) -> Optional[models.Friendship]:
    return db.query(models.Friendship).filter(models.Friendship.id == request_id).first()


def accept_friend_request(db: Session, request: models.Friendship) -> Optional[models.Friendship]:
    if not request or request.status != "pending":
        return None
    request.status = "accepted"
    request.accepted_at = datetime.utcnow()
    request.updated_at = datetime.utcnow()
    db.add(request)
    exists_inverse = db.query(models.Friendship).filter(
        models.Friendship.user_id == request.friend_id,
        models.Friendship.friend_id == request.user_id
    ).first()
    if not exists_inverse:
        inverse = models.Friendship(
            user_id=request.friend_id,
            friend_id=request.user_id,
            status="accepted",
            created_at=datetime.utcnow(),
            accepted_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(inverse)
    db.commit()
    db.refresh(request)
    return request


def reject_friend_request(db: Session, request: models.Friendship) -> Optional[models.Friendship]:
    if not request or request.status != "pending":
        return None
    request.status = "rejected"
    request.updated_at = datetime.utcnow()
    db.add(request)
    db.commit()
    db.refresh(request)
    return request


def block_user(db: Session, user_id: int, block_id: int) -> models.Friendship:
    existing = db.query(models.Friendship).filter_by(user_id=user_id, friend_id=block_id).first()
    if existing:
        existing.status = "blocked"
        existing.updated_at = datetime.utcnow()
        db.add(existing)
    else:
        existing = models.Friendship(
            user_id=user_id,
            friend_id=block_id,
            status="blocked",
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )
        db.add(existing)

    inverse = db.query(models.Friendship).filter_by(user_id=block_id, friend_id=user_id).first()
    if inverse and inverse.status != "blocked":
        db.delete(inverse)

    db.commit()
    db.refresh(existing)
    return existing


def cancel_friend_request(db: Session, request_id: int, user_id: int) -> bool:
    f = db.query(models.Friendship).filter_by(id=request_id, user_id=user_id, status="pending").first()
    if not f:
        return False
    db.delete(f)
    db.commit()
    return True


def remove_friend(db: Session, user_id: int, friend_id: int) -> bool:
    f1 = db.query(models.Friendship).filter_by(user_id=user_id, friend_id=friend_id).first()
    f2 = db.query(models.Friendship).filter_by(user_id=friend_id, friend_id=user_id).first()
    if not f1 and not f2:
        return False
    if f1:
        db.delete(f1)
    if f2:
        db.delete(f2)
    db.commit()
    return True


def get_sent_friend_requests(db: Session, user_id: int) -> List[models.Friendship]:
    return (
        db.query(models.Friendship)
        .options(joinedload(models.Friendship.receiver))
        .filter_by(user_id=user_id, status="pending")
        .order_by(models.Friendship.created_at.desc())
        .all()
    )


def get_friends_for_user(db: Session, user_id: int) -> List[models.User]:
    sent_ids = {
        f.friend_id
        for f in db.query(models.Friendship.friend_id)
        .filter_by(user_id=user_id, status="accepted")
        .all()
    }
    received_ids = {
        f.user_id
        for f in db.query(models.Friendship.user_id)
        .filter_by(friend_id=user_id, status="accepted")
        .all()
    }
    friend_ids = sent_ids | received_ids
    if not friend_ids:
        return []
    return db.query(models.User).filter(models.User.id.in_(list(friend_ids))).all()

def search_users(db: Session, q: str, page: int = 1, page_size: int = 20) -> Dict[str, Any]:
    if not q or not str(q).strip():
        return {"total": 0, "items": []}

    term = f"%{q.strip().lower()}%"

    name_or_email = or_(
        func.lower(models.User.name).like(term),
        func.lower(models.User.email).like(term),
    )

    total_q = db.query(func.count(models.User.id)).filter(
        models.User.is_active == True,
        name_or_email,
    )
    total = int(total_q.scalar() or 0)

    items_q = (
        db.query(
            models.User.id.label("id"),
            models.User.email.label("email"),
            models.User.name.label("name"),
            models.User.bio.label("bio"),
            models.User.avatar_url.label("avatar_url"),
            models.User.is_active.label("is_active"),
            models.User.created_at.label("created_at"),
            func.count(models.Game.id).label("games_count"),
        )
        .outerjoin(models.Game, models.Game.user_id == models.User.id)
        .filter(models.User.is_active == True, name_or_email)
        .group_by(models.User.id)
        .order_by(models.User.name.asc())
        .offset(max(0, (page - 1)) * page_size)
        .limit(page_size)
    )

    rows = items_q.all()

    items = []
    for r in rows:
        items.append({
            "id": r.id,
            "email": r.email,
            "name": r.name,
            "bio": r.bio,
            "avatar_url": r.avatar_url,
            "is_active": bool(r.is_active),
            "created_at": r.created_at.isoformat() if r.created_at is not None else None,
            "games_count": int(r.games_count or 0),
        })

    return {"total": total, "items": items}


def get_friend_requests_for_user(db: Session, user_id: int, only_pending: bool = True, limit: Optional[int] = None) -> List[models.Friendship]:
    q = (
        db.query(models.Friendship)
        .options(joinedload(models.Friendship.requester))
        .filter(models.Friendship.friend_id == user_id)
    )

    if only_pending:
        q = q.filter(models.Friendship.status == "pending")

    q = q.order_by(models.Friendship.created_at.desc())

    if limit:
        q = q.limit(int(limit))

    return q.all()
