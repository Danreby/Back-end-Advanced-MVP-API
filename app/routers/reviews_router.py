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
