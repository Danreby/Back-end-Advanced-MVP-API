from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, Response, Request, Cookie
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta, datetime
import os

from .. import schemas, crud, auth, models
from ..database import get_db
from ..mail import send_email
from ..auth import utils as token_utils, crud as token_crud
from dotenv import load_dotenv

load_dotenv()

# colocar email de confirmação
EMAIL_CONFIRM_URL = os.getenv("EMAIL_CONFIRM_URL", "http://localhost:8000")

router = APIRouter(prefix="/auth", tags=["auth"])

REMEMBER_COOKIE_NAME = "remember"
REMEMBER_DAYS = 30
REMEMBER_MAX_AGE = REMEMBER_DAYS * 24 * 60 * 60

# ------------------ REGISTER ------------------
@router.post('/register', response_model=schemas.UserOut)
def register(user_in: schemas.UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail='Email already registered')
    hashed = auth.get_password_hash(user_in.password)
    user = crud.create_user(db, user_in, hashed, is_active=False)

    access_token_expires = timedelta(hours=24)
    token = auth.create_access_token(
        data={"sub": user.email, "type": "email_confirm"},
        expires_delta=access_token_expires
    )

    confirm_url = f"{EMAIL_CONFIRM_URL}/auth/confirm?token={token}"

    subject = "Confirme seu e-mail"
    body = (
        f"Olá {user.name or user.email},\n\n"
        f"Por favor confirme seu endereço de e-mail clicando no link abaixo:\n\n"
        f"{confirm_url}\n\n"
        "Se não se registrou, ignore esta mensagem."
    )

    background_tasks.add_task(send_email, subject, [user.email], body)

    return user


# ------------------ CONFIRM ------------------
@router.get('/confirm')
def confirm_email(token: str, db: Session = Depends(get_db)):
    from jose import JWTError, jwt
    try:
        payload = jwt.decode(token, auth.SECRET_KEY, algorithms=[auth.ALGORITHM])
        token_type = payload.get("type")
        if token_type != "email_confirm":
            raise HTTPException(status_code=400, detail="Invalid token type")
        email = payload.get("sub")
        if not email:
            raise HTTPException(status_code=400, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=400, detail="Invalid or expired token")

    user = crud.activate_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {"message": "Email confirmado com sucesso", "email": user.email}


# ------------------ LOGIN ------------------
@router.post("/login")
def login(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please confirm your email before login."
        )

    access_token_expires = timedelta(minutes=auth.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = auth.create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )

    remember = request.query_params.get("remember") == "true"
    if remember:
        raw_token = token_utils.generate_raw_token()
        token_crud.create_remember_token(
            db=db,
            user=user,
            raw_token=raw_token,
            expires_at=token_utils.token_expiration(days=REMEMBER_DAYS),
            user_agent=request.headers.get("user-agent"),
            ip=request.client.host if request.client else None
        )
        response.set_cookie(
            key=REMEMBER_COOKIE_NAME,
            value=raw_token,
            max_age=REMEMBER_MAX_AGE,
            httponly=True,
            secure=False,
            samesite="lax",
            path="/"
        )

    return {"access_token": access_token, "token_type": "bearer"}


# ------------------ LOGOUT ------------------
@router.post("/logout")
def logout(
    response: Response,
    db: Session = Depends(get_db),
    remember_cookie: str | None = Cookie(default=None, alias=REMEMBER_COOKIE_NAME)
):
    if remember_cookie:
        token_obj = token_crud.get_remember_token_by_raw(db, remember_cookie)
        if token_obj:
            token_crud.revoke_remember_token(db, token_obj)

    response.delete_cookie(key=REMEMBER_COOKIE_NAME, path="/")
    return {"message": "Logout realizado com sucesso"}
