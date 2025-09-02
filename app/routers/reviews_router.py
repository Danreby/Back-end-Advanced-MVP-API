from typing import Optional, List, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, desc
from app.database import get_db
from app import models, schemas
from app.auth import get_current_user

router = APIRouter(prefix="/reviews", tags=["reviews"])

MAX_LIMIT = 500


@router.get("/", response_model=schemas.PaginatedReviews)
def list_public_reviews(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    if skip < 0:
        skip = 0
    if limit <= 0:
        limit = 50
    if limit > MAX_LIMIT:
        limit = MAX_LIMIT

    q = db.query(models.Review).filter(models.Review.is_public == True)
    total = q.count()
    items = (
        q.options(joinedload(models.Review.user), joinedload(models.Review.game))
         .order_by(models.Review.created_at.desc())
         .offset(skip).limit(limit).all()
    )
    return {"total": total, "items": items}


@router.get("/my", response_model=schemas.PaginatedReviews)
def list_my_reviews(skip: int = 0, limit: int = 50, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    if skip < 0:
        skip = 0
    if limit <= 0:
        limit = 50
    if limit > MAX_LIMIT:
        limit = MAX_LIMIT

    q = db.query(models.Review).filter(models.Review.user_id == current_user.id)
    total = q.count()
    items = (
        q.options(joinedload(models.Review.user), joinedload(models.Review.game))
         .order_by(models.Review.created_at.desc())
         .offset(skip).limit(limit).all()
    )
    return {"total": total, "items": items}


@router.get("/me", response_model=Optional[schemas.ReviewOut])
def get_my_review(
    game_id: Optional[int] = None,
    external_guid: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user = Depends(get_current_user),
):
    if not game_id and not external_guid:
        raise HTTPException(status_code=400, detail="game_id or external_guid required")

    q = db.query(models.Review).filter(models.Review.user_id == current_user.id)
    if game_id:
        q = q.filter(models.Review.game_id == game_id)
    if external_guid:
        q = q.filter(models.Review.external_guid == external_guid)

    review = q.order_by(models.Review.updated_at.desc()).first()
    if not review:
        return None
    return review


@router.post("/upsert", response_model=schemas.ReviewOut)
def upsert_review(payload: schemas.ReviewUpsert, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    game = None
    if payload.game_id:
        game = db.get(models.Game, payload.game_id)
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")
    elif payload.external_guid:
        game = db.query(models.Game).filter_by(external_guid=payload.external_guid).first()
        if not game:
            game = models.Game(external_guid=payload.external_guid, name=payload.name or "Unknown", user_id=current_user.id)
            db.add(game)
            db.commit()
            db.refresh(game)
    else:
        raise HTTPException(status_code=400, detail="game_id or external_guid required")

    review = db.query(models.Review).filter_by(user_id=current_user.id, game_id=game.id).first()
    if review:
        for k, v in payload.dict(exclude_unset=True).items():
            if k in ("rating", "review_text", "is_public"):
                setattr(review, k, v)
    else:
        review = models.Review(
            user_id=current_user.id,
            game_id=game.id,
            rating=payload.rating,
            review_text=payload.review_text,
            is_public=payload.is_public if payload.is_public is not None else True,
            external_guid=payload.external_guid if payload.external_guid else None
        )
        db.add(review)

    db.commit()
    db.refresh(review)
    return review


@router.patch("/autosave", response_model=schemas.ReviewOut)
def autosave_review(payload: schemas.ReviewAutoSave, db: Session = Depends(get_db), current_user = Depends(get_current_user)):
    upsert_payload = schemas.ReviewUpsert(
        game_id=payload.game_id,
        external_guid=payload.external_guid,
        rating=payload.rating,
        review_text=payload.review_text,
        is_public=payload.is_public,
        name=getattr(payload, "name", None),
    )
    return upsert_review(upsert_payload, db=db, current_user=current_user)


@router.post("/game/{game_id}", response_model=schemas.ReviewOut)
def create_review(game_id: int, payload: schemas.ReviewCreate, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    game = db.get(models.Game, game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    existing = db.query(models.Review).filter_by(user_id=current_user.id, game_id=game_id).first()
    if existing:
        raise HTTPException(status_code=409, detail="Review already exists")
    review = models.Review(**payload.dict(), user_id=current_user.id, game_id=game_id)
    db.add(review)
    db.commit()
    db.refresh(review)
    return review


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


@router.delete("/{review_id}", status_code=204)
def delete_review(review_id: int, db: Session = Depends(get_db), current_user=Depends(get_current_user)):
    review = db.query(models.Review).filter_by(id=review_id, user_id=current_user.id).first()
    if not review:
        raise HTTPException(status_code=404, detail="Review not found")
    db.delete(review)
    db.commit()
    return


@router.get("/grouped", response_model=schemas.PaginatedReviews)
def list_public_reviews_grouped(
    skip: int = 0,
    limit: int = 5,
    reviews_per_game_limit: int = 200,
    db: Session = Depends(get_db),
):
    if skip < 0:
        skip = 0
    if limit <= 0:
        limit = 5
    if reviews_per_game_limit <= 0:
        reviews_per_game_limit = 200
    total_groups = db.query(func.count(func.distinct(models.Review.game_id))).filter(models.Review.is_public == True).scalar() or 0

    if total_groups == 0:
        return {"total": 0, "items": []}

    group_q = (
        db.query(
            models.Review.game_id,
            func.count(models.Review.id).label("reviews_count"),
            func.avg(models.Review.rating).label("avg_rating"),
        )
        .filter(models.Review.is_public == True)
        .group_by(models.Review.game_id)
        .order_by(desc("reviews_count"), desc("avg_rating"))
        .offset(skip)
        .limit(limit)
    )
    group_rows = group_q.all()
    game_ids = [int(row.game_id) for row in group_rows]

    if not game_ids:
        return {"total": total_groups, "items": []}

    reviews_q = (
        db.query(models.Review)
        .options(joinedload(models.Review.user), joinedload(models.Review.game))
        .filter(models.Review.is_public == True, models.Review.game_id.in_(game_ids))
        .order_by(models.Review.created_at.desc())
    )
    reviews = reviews_q.all()

    reviews_by_game = {gid: [] for gid in game_ids}
    for r in reviews:
        gid = r.game_id
        if gid in reviews_by_game:
            reviews_by_game[gid].append(r)

    flattened = []
    for gid in game_ids:
        items_for_game = reviews_by_game.get(gid, [])[:reviews_per_game_limit]
        flattened.extend(items_for_game)

    return {"total": total_groups, "items": flattened}
