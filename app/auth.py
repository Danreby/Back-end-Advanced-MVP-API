import os
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from dotenv import load_dotenv

from . import crud, schemas, models
from .database import get_db

import secrets
import hashlib

load_dotenv()

# Config (leia de .env, com fallback)
SECRET_KEY = os.getenv("SECRET_KEY", "troque_esta_chave")
ALGORITHM = os.getenv("ALGORITHM", "HS256")
ACCESS_TOKEN_EXPIRE_MINUTES = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "60"))

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# OAuth2 scheme (rota de obtenção do token)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/login")


# -----------------------
# Password helpers
# -----------------------
def verify_password(plain_password: str, hashed_password: str) -> bool:
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except Exception:
        return False


def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)


# -----------------------
# Authentication helpers
# -----------------------
def authenticate_user(db: Session, email: str, password: str) -> Optional[models.User]:
    user = crud.get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(subject: str, expires_delta: Optional[timedelta] = None, extra_claims: Optional[Dict[str, Any]] = None) -> str:
    now = datetime.utcnow()
    if expires_delta:
        expire = now + expires_delta
    else:
        expire = now + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)

    payload: Dict[str, Any] = {
        "sub": subject,
        "iat": now,
        "exp": expire,
    }

    if extra_claims:
        for k, v in extra_claims.items():
            if k not in payload:
                payload[k] = v

    token = jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)
    return token


def decode_access_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])


# -----------------------
# FastAPI dependencias
# -----------------------
def get_current_user(token: str = Depends(oauth2_scheme), db: Session = Depends(get_db)) -> models.User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = decode_access_token(token)
        email: Optional[str] = payload.get("sub")
        if email is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = crud.get_user_by_email(db, email=email)
    if not user:
        raise credentials_exception
    return user


def get_current_active_user(current_user: models.User = Depends(get_current_user)) -> models.User:
    is_active = getattr(current_user, "is_active", True)
    if not is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user


# -----------------------
# Remember / Persistent token helpers (opcional)
# -----------------------
def generate_raw_token(n_bytes: int = 48) -> str:
    return secrets.token_urlsafe(n_bytes)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def token_expiration(days: int = 30) -> datetime:
    return datetime.utcnow() + timedelta(days=days)