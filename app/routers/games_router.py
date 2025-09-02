from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func
from app.database import get_db
from app import crud, schemas, models
from app.auth import get_current_user
from app.models import Game, Review

router = APIRouter(prefix="/games", tags=["games"])


def serialize_game_for_front(game: Game) -> Dict[str, Any]:
    raw_desc = game.description or game.summary or ""
    safe_desc = raw_desc.replace("<script", "&lt;script").replace("</script>", "&lt;/script&gt;")

    image_obj = None
    if getattr(game, "cover_url", None):
        image_obj = {"superUrl": game.cover_url, "mediumUrl": game.cover_url, "smallUrl": game.cover_url}
    elif getattr(game, "image", None):
        img = game.image
        image_obj = {"superUrl": getattr(img, "super_url", None), "mediumUrl": getattr(img, "medium_url", None), "smallUrl": getattr(img, "small_url", None)}

    platforms = []
    if getattr(game, "platforms", None):
        try:
            platforms = [p.name for p in game.platforms]
        except Exception:
            platforms = []

    publishers = []
    if getattr(game, "publishers", None):
        try:
            publishers = [p.name for p in game.publishers]
        except Exception:
            publishers = []

    genres = []
    if getattr(game, "genres", None):
        try:
            genres = [g.name for g in game.genres]
        except Exception:
            genres = []

    avg_rating = getattr(game, "avg_rating", None)
    reviews_count = getattr(game, "reviews_count", None)

    payload = {
        "id": game.id,
        "externalGuid": getattr(game, "external_guid", None),
        "name": game.name,
        "releaseDate": game.release_date.isoformat() if getattr(game, "release_date", None) else None,
        "releaseDateFormatted": game.release_date.strftime("%d/%m/%Y") if getattr(game, "release_date", None) else None,
        "platforms": platforms,
        "publishers": publishers,
        "genres": genres,
        "image": image_obj,
        "descriptionHtml": safe_desc,
        "status": getattr(game, "status", None),
        "startDate": getattr(game, "start_date", None).isoformat() if getattr(game, "start_date", None) else None,
        "finishDate": getattr(game, "finish_date", None).isoformat() if getattr(game, "finish_date", None) else None,
        "avgRating": avg_rating,
        "reviewsCount": reviews_count,
        "createdAt": getattr(game, "created_at", None).isoformat() if getattr(game, "created_at", None) else None,
        "updatedAt": getattr(game, "updated_at", None).isoformat() if getattr(game, "updated_at", None) else None,
    }
    return payload


# --- Create game (same) ---
@router.post("/", response_model=schemas.GameOut, status_code=status.HTTP_201_CREATED)
def create_game(game_in: schemas.GameCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    g = crud.create_game(db, current_user.id, game_in)
    return g


# --- Listagem de jogos do user paginados (same) ---
@router.get("/", response_model=schemas.PaginatedGames)
def list_my_games(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    items = crud.get_games_by_user(db, current_user.id, skip=skip, limit=limit)
    total = db.query(models.Game).filter(models.Game.user_id == current_user.id).count()
    return {"total": total, "items": items}


# --- Public listing all games grouped by external_guid (same) ---
@router.get("/all")
def list_all_games(db: Session = Depends(get_db)) -> List[Dict]:
    row_number = func.row_number().over(
        partition_by=Game.external_guid,
        order_by=func.coalesce(Game.updated_at, Game.created_at).desc()
    ).label("rn")

    reviews_count = func.count(Game.id).over(partition_by=Game.external_guid).label("reviews_count")

    subq = (
        db.query(
            Game.external_guid.label("external_guid"),
            Game.id.label("id"),
            Game.name.label("name"),
            Game.cover_url.label("cover_url"),
            Game.description.label("description"),
            Game.status.label("status"),
            Game.start_date.label("start_date"),
            Game.finish_date.label("finish_date"),
            Game.created_at.label("created_at"),
            Game.updated_at.label("updated_at"),
            reviews_count,
            row_number
        )
        .filter(Game.external_guid.isnot(None))
        .subquery()
    )

    rows = db.query(subq).filter(subq.c.rn == 1).all()

    result = []
    for r in rows:
        result.append({
            "external_guid": r.external_guid,
            "reviews_count": int(r.reviews_count),
            "id": r.id,
            "name": r.name,
            "cover_url": r.cover_url,
            "description": r.description,
            "status": r.status,
            "start_date": r.start_date.isoformat() if r.start_date else None,
            "finish_date": r.finish_date.isoformat() if r.finish_date else None,
            "created_at": r.created_at.isoformat() if r.created_at else None,
            "updated_at": r.updated_at.isoformat() if r.updated_at else None,
        })

    return result


# --- Public game detail (no auth) ---
@router.get("/{game_id}")
def get_game_public(game_id: int, db: Session = Depends(get_db)):
    g = crud.get_game(db, game_id)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    payload = serialize_game_for_front(g)
    return payload


# --- Game detail + user review (requires auth) ---
@router.get("/{game_id}/me")
def get_game_with_my_review(game_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    g = crud.get_game(db, game_id)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")

    payload = serialize_game_for_front(g)

    review = db.query(models.Review).filter_by(user_id=current_user.id, game_id=g.id).order_by(models.Review.updated_at.desc()).first()
    payload["userReview"] = None
    if review:
        payload["userReview"] = {
            "id": review.id,
            "rating": review.rating,
            "reviewText": review.review_text,
            "isPublic": review.is_public,
            "createdAt": review.created_at.isoformat() if review.created_at else None,
            "updatedAt": review.updated_at.isoformat() if review.updated_at else None,
        }

    return payload


# --- Update game (only owner) ---
@router.put("/{game_id}", response_model=schemas.GameOut)
def update_game(game_id: int, payload: schemas.GameUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    g = crud.get_game(db, game_id)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    if g.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    updated = crud.update_game(db, g, payload.dict(exclude_unset=True))
    return updated


# --- Delete game (only owner) ---
@router.delete("/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_game(game_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    g = crud.get_game(db, game_id)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    if g.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    crud.delete_game(db, g)
    return {}


# --- Reviews nested endpoints kept for compatibility (calls into crud) ---
@router.get("/{game_id}/reviews", response_model=schemas.PaginatedReviews)
def list_reviews(game_id: int, public_only: bool = True, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    base_q = db.query(Review).filter(Review.game_id == game_id)
    if public_only:
        base_q = base_q.filter(Review.is_public == True)

    total = base_q.count()

    items = (
        base_q
        .options(
            joinedload(Review.user),
            joinedload(Review.game)
        )
        .order_by(Review.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    return {"total": total, "items": items}


# --- Upsert game status (single endpoint) ---
@router.post("/upsert-status", response_model=Dict)
def upsert_game_status(payload: Dict, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    game_id = payload.get("id")
    external_guid = payload.get("external_guid")
    status_val = payload.get("status")

    if not status_val:
        raise HTTPException(status_code=400, detail="status is required")

    game = None
    if game_id:
        game = crud.get_game(db, game_id)
    elif external_guid:
        game = db.query(models.Game).filter_by(external_guid=external_guid, user_id=current_user.id).first()
        if not game:
            game = models.Game(external_guid=external_guid, name=payload.get("name") or external_guid, user_id=current_user.id)
            db.add(game)
            db.commit()
            db.refresh(game)
    else:
        raise HTTPException(status_code=400, detail="id or external_guid required")

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    if getattr(game, "user_id", None) and game.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")

    game.status = status_val
    db.add(game)
    db.commit()
    db.refresh(game)

    payload_out = serialize_game_for_front(game)
    payload_out["userData"] = {"status": status_val}
    return payload_out
