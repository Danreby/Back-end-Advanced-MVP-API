# app/routers/games_router.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.database import get_db
from app import crud, schemas
from app.auth import get_current_user  # seu dependency que retorna user model

router = APIRouter(prefix="/games", tags=["games"])

# --- Create a game for the authenticated user ---
@router.post("/", response_model=schemas.GameOut, status_code=status.HTTP_201_CREATED)
def create_game(game_in: schemas.GameCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    g = crud.create_game(db, current_user.id, game_in)
    return g

# --- List games of the current user (with pagination) ---
@router.get("/", response_model=schemas.PaginatedGames)
def list_my_games(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    items = crud.get_games_by_user(db, current_user.id, skip=skip, limit=limit)
    total = db.query(models.Game).filter(models.Game.user_id == current_user.id).count()  # import models below or use another query
    return {"total": total, "items": items}

# --- Get single game (must be owner to see private details) ---
@router.get("/{game_id}", response_model=schemas.GameOut)
def get_game(game_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    g = crud.get_game(db, game_id)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    if g.user_id != current_user.id:
        # if you allow public access to game info, modify this; here we restrict to owner
        raise HTTPException(status_code=403, detail="Not authorized")
    return g

# --- Update a game (owner only) ---
@router.put("/{game_id}", response_model=schemas.GameOut)
def update_game(game_id: int, payload: schemas.GameUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    g = crud.get_game(db, game_id)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    if g.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    updated = crud.update_game(db, g, payload.dict(exclude_unset=True))
    return updated

# --- Delete a game (owner only) ---
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

# Create a review for a game (authenticated user). If a review by same user exists -> 409
@router.post("/{game_id}/reviews", response_model=schemas.ReviewOut, status_code=status.HTTP_201_CREATED)
def create_review(game_id: int, review_in: schemas.ReviewCreate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    g = crud.get_game(db, game_id)
    if not g:
        raise HTTPException(status_code=404, detail="Game not found")
    # you may allow reviews only for user's own games or for any game - here we allow any authenticated user
    r = crud.create_review(db, current_user.id, game_id, review_in)
    if not r:
        raise HTTPException(status_code=409, detail="Review already exists for this user & game")
    return r

# Update a review (only review owner)
@router.put("/{game_id}/reviews/{review_id}", response_model=schemas.ReviewOut)
def update_review(game_id: int, review_id: int, payload: schemas.ReviewUpdate, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    r = crud.get_review(db, review_id)
    if not r or r.game_id != game_id:
        raise HTTPException(status_code=404, detail="Review not found")
    if r.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    updated = crud.update_review(db, r, payload.dict(exclude_unset=True))
    return updated

# Delete a review (only owner)
@router.delete("/{game_id}/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_review(game_id: int, review_id: int, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    r = crud.get_review(db, review_id)
    if not r or r.game_id != game_id:
        raise HTTPException(status_code=404, detail="Review not found")
    if r.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not authorized")
    crud.delete_review(db, r)
    return {}

# List public reviews for a game (no auth required)
@router.get("/{game_id}/reviews", response_model=schemas.PaginatedReviews)
def list_reviews(game_id: int, public_only: bool = True, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    total, items = crud.get_reviews_by_game(db, game_id, public_only=public_only, skip=skip, limit=limit)
    return {"total": total, "items": items}
