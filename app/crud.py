from sqlalchemy.orm import Session
from . import models, schemas

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
