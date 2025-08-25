from sqlalchemy.orm import Session
from . import models, schemas
from typing import List, Optional
from datetime import datetime

def get_user_by_email(db: Session, email: str):
    return db.query(models.User).filter(models.User.email == email).first()

def create_user(db: Session, user: schemas.UserCreate, hashed_password: str, is_active: bool = False):
    db_user = models.User(email=user.email, name=user.name, hashed_password=hashed_password, is_active=is_active)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user

def activate_user_by_email(db: Session, email: str):
    user = db.query(models.User).filter(models.User.email == email).first()
    if not user:
        return None
    user.is_active = True
    db.add(user)
    db.commit()
    db.refresh(user)
    return user

# ---------- Games ----------
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
    )
    db.add(g)
    db.commit()
    db.refresh(g)
    return g

def get_game(db: Session, game_id: int) -> Optional[models.Game]:
    return db.query(models.Game).filter(models.Game.id == game_id).first()

def get_games_by_user(db: Session, user_id: int, skip: int = 0, limit: int = 50) -> List[models.Game]:
    return db.query(models.Game).filter(models.Game.user_id == user_id).offset(skip).limit(limit).all()

def delete_game(db: Session, game: models.Game):
    db.delete(game)
    db.commit()

def update_game(db: Session, game: models.Game, data) -> models.Game:
    for k, v in data.items():
        if v is not None:
            setattr(game, k, v)
    game.updated_at = datetime.utcnow()
    db.add(game)
    db.commit()
    db.refresh(game)
    return game

# ---------- Reviews ----------
def create_review(db: Session, user_id: int, game_id: int, review_in) -> models.Review:
    existing = db.query(models.Review).filter(models.Review.user_id == user_id, models.Review.game_id == game_id).first()
    if existing:
        return None
    r = models.Review(
        user_id=user_id,
        game_id=game_id,
        rating=review_in.rating,
        review_text=review_in.review_text,
        is_public=review_in.is_public if review_in.is_public is not None else True
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r

def get_review(db: Session, review_id: int) -> Optional[models.Review]:
    return db.query(models.Review).filter(models.Review.id == review_id).first()

def update_review(db: Session, review: models.Review, data) -> models.Review:
    for k, v in data.items():
        if v is not None:
            setattr(review, k, v)
    review.updated_at = datetime.utcnow()
    db.add(review)
    db.commit()
    db.refresh(review)
    return review

def delete_review(db: Session, review: models.Review):
    db.delete(review)
    db.commit()

def get_reviews_by_game(db: Session, game_id: int, public_only: bool = True, skip: int = 0, limit: int = 50):
    q = db.query(models.Review).filter(models.Review.game_id == game_id)
    if public_only:
        q = q.filter(models.Review.is_public == True)
    total = q.count()
    items = q.offset(skip).limit(limit).all()
    return total, items
