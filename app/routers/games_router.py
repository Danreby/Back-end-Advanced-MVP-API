from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app import crud, schemas, models
from app.auth import get_current_user

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
