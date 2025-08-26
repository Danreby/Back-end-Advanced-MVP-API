from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
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
def list_all_games(db: Session = Depends(get_db)):
    results = (
        db.query(
            Game.external_guid,
            func.count(Game.id).label("reviews_count"),
            func.max(Game.status).label("status"),
        )
        .group_by(Game.external_guid)
        .all()
    )

    enriched = []
    for r in results:
        try:
            gb_data = get_game_by_guid(r.external_guid)
        except Exception as e:
            print(f"❌ Erro GiantBomb GUID={r.external_guid}: {e}")
            gb_data = None

        enriched.append({
            "external_guid": r.external_guid,
            "name": gb_data.get("name") if gb_data else None,
            "reviews_count": r.reviews_count,
            "status": r.status,
            "description": gb_data.get("deck") if gb_data else None,
            "release_date": gb_data.get("original_release_date") if gb_data else None,
            "platforms": gb_data.get("platforms") if gb_data else None,
            "developers": gb_data.get("developers") if gb_data else None,
            "publishers": gb_data.get("publishers") if gb_data else None,
            "genres": gb_data.get("genres") if gb_data else None,
            "image": gb_data.get("image") if gb_data else None,
        })

    return enriched

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