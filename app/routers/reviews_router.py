from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from typing import Optional
from app.database import get_db
from app import schemas, models
from app.auth import get_current_user

router = APIRouter(prefix="/reviews", tags=["reviews"])

@router.get("/", response_model=schemas.PaginatedReviews)
def list_public_reviews(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    q = db.query(models.Review).filter(models.Review.is_public == True)
    total = q.count()
    items = (
        q.options(joinedload(models.Review.user), joinedload(models.Review.game))
         .order_by(models.Review.created_at.desc())
         .offset(skip).limit(limit).all()
    )
    return {"total": total, "items": items}

@router.get("/me", response_model=schemas.PaginatedReviews)
def list_my_reviews(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    q = db.query(models.Review).filter(models.Review.user_id == current_user.id)
    total = q.count()
    items = (
        q.options(joinedload(models.Review.user), joinedload(models.Review.game))
         .order_by(models.Review.created_at.desc())
         .offset(skip).limit(limit).all()
    )
    return {"total": total, "items": items}


# Criar review para um game
@router.post("/game/{game_id}", response_model=schemas.ReviewOut)
def create_review(game_id: int, payload: schemas.ReviewCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    game = db.query(models.Game).get(game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    review = models.Review(**payload.dict(), user_id=current_user.id, game_id=game_id)
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


# Atualizar review
@router.put("/{review_id}", response_model=schemas.ReviewOut)
def update_review(review_id: int, payload: schemas.ReviewUpdate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    review = db.query(models.Review).filter_by(id=review_id, user_id=current_user.id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    for field, value in payload.dict(exclude_unset=True).items():
        setattr(review, field, value)
    db.commit()
    db.refresh(review)
    return review


# Deletar review
@router.delete("/{review_id}", status_code=204)
def delete_review(review_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    review = db.query(models.Review).filter_by(id=review_id, user_id=current_user.id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    db.delete(review)
    db.commit()
    return
