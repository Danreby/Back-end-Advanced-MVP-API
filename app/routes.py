from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import os

from .. import schemas, crud, auth
from ..database import get_db
from ..mail import send_email
from dotenv import load_dotenv

load_dotenv()

EMAIL_CONFIRM_URL = os.getenv("EMAIL_CONFIRM_URL", "http://localhost:8000")

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post('/register', response_model=schemas.UserOut)
def register(user_in: schemas.UserCreate, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    existing = crud.get_user_by_email(db, user_in.email)
    if existing:
        raise HTTPException(status_code=400, detail='Email already registered')
    hashed = auth.get_password_hash(user_in.password)
    # cria usuário inativo até confirmação
    user = crud.create_user(db, user_in, hashed, is_active=False)

    # cria token de confirmação (expira em 24h)
    access_token_expires = timedelta(hours=24)
    token = auth.create_access_token(data={"sub": user.email, "type": "email_confirm"}, expires_delta=access_token_expires)

    confirm_url = f"{EMAIL_CONFIRM_URL}/auth/confirm?token={token}"

    # corpo do email (pode usar HTML)
    subject = "Confirme seu e-mail"
    body = f"Olá {user.name or user.email},\n\nPor favor confirme seu endereço de e-mail clicando no link abaixo:\n\n{confirm_url}\n\nSe não se registrou, ignore esta mensagem."

    # envia em background
    background_tasks.add_task(send_email, subject, [user.email], body)

    return user

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
