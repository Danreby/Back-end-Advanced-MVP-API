from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict
from sqlalchemy import func
from app.database import get_db
from app import crud, schemas, models
from app.auth import get_current_user
from app.models import Game
from app.services.giantbomb import get_game_by_guid

router = APIRouter(prefix="/games", tags=["games"])

# --- Criar um jogo ---
@router.post("/", response_model=schemas.GameOut, status_code=status.HTTP_201_CREATED)
def create_game(game_in: schemas.GameCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    g = crud.create_game(db, current_user.id, game_in)
    return g

# --- Listagem de jogos do user paginados ---
@router.get("/", response_model=schemas.PaginatedGames)
def list_my_games(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    items = crud.get_games_by_user(db, current_user.id, skip=skip, limit=limit)
    total = db.query(models.Game).filter(models.Game.user_id == current_user.id).count()
    return {"total": total, "items": items}

# --- Get para todos os jogos ---
@router.get("/all")
def list_all_games(db: Session = Depends(get_db)) -> List[Dict]:
    # window: numero da linha por external_guid ordenado por updated_at/created_at desc
    row_number = func.row_number().over(
        partition_by=Game.external_guid,
        order_by=func.coalesce(Game.updated_at, Game.created_at).desc()
    ).label("rn")

    # count por grupo (external_guid)
    reviews_count = func.count(Game.id).over(partition_by=Game.external_guid).label("reviews_count")

    # subquery que traz cada linha junto com rn e reviews_count
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


# --- Get de um jogo ---
@router.get("/{game_id}", response_model=schemas.GameOut)
def get_game(game_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    g = crud.get_game(db, game_id)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    if g.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    return g

# --- Atualizar um jgoo ---
@router.put("/{game_id}", response_model=schemas.GameOut)
def update_game(game_id: int, payload: schemas.GameUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    g = crud.get_game(db, game_id)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    if g.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    updated = crud.update_game(db, g, payload.dict(exclude_unset=True))
    return updated

# --- Deletar um jogo ---
@router.delete("/{game_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_game(game_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    g = crud.get_game(db, game_id)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    if g.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    crud.delete_game(db, g)
    return {}

# ---------------- Reviews endpoints ----------------

# Criar review de um jogo
@router.post("/{game_id}/reviews", response_model=schemas.ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(game_id: int, review_in: schemas.ReviewCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    g = crud.get_game(db, game_id)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    r = crud.create_review(db, current_user.id, game_id, review_in)
    if not r:
        raise HTTPException(status_code=409, detail="Review already exists for this user & game")
    return r

# --- Atualizar review ---
@router.put("/{game_id}/reviews/{review_id}", response_model=schemas.ReviewOut)
def update_review(game_id: int, review_id: int, payload: schemas.ReviewUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    r = crud.get_review(db, review_id)
    if not r or r.game_id != game_id:
        raise HTTPException(status_code=404, detail="Review not found")
    if r.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    updated = crud.update_review(db, r, payload.dict(exclude_unset=True))
    return updated

# --- Deletar review ---
@router.delete("/{game_id}/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(game_id: int, review_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    r = crud.get_review(db, review_id)
    if not r or r.game_id != game_id:
        raise HTTPException(status_code=404, detail="Review not found")
    if r.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    crud.delete_review(db, r)
    return {}

# --- Listagem das reviews de um jogo ---
@router.get("/{game_id}/reviews", response_model=schemas.PaginatedReviews)
def list_reviews(game_id: int, public_only: bool = True, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    total, items = crud.get_reviews_by_game(db, game_id, public_only=public_only, skip=skip, limit=limit)
    return {"total": total, "items": items}