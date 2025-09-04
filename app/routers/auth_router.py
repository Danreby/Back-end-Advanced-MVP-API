import os
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
from fastapi.responses import RedirectResponse, HTMLResponse

from .. import schemas, models, crud, auth
from ..database import get_db
from ..mail import (
    send_confirmation_email,
    get_dev_confirmations,
    pop_dev_confirmation,
    ENABLE_DEV_EMAIL_ENDPOINTS,
    DISABLE_EMAILS,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register")
async def register(user: schemas.UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(models.User).filter(models.User.email == user.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email já registrado.")

    new_user = models.User(
        name=user.name,
        email=user.email,
        hashed_password=auth.get_password_hash(user.password),
        is_active=False,
    )
    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    token = auth.create_confirmation_token(new_user.email)

    confirmation_url = await send_confirmation_email(new_user.email, token)

    return {
        "message": "Conta criada com sucesso! Use o link abaixo para confirmar seu e-mail.",
        "confirmation_url": confirmation_url,
    }


@router.post("/login", response_model=schemas.Token)
def login(
    background_tasks: BackgroundTasks,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    user = auth.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not getattr(user, "is_active", False):
        token = auth.create_confirmation_token(user.email)
        background_tasks.add_task(send_confirmation_email, user.email, token)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Account is not active. Confirmation email sent.",
        )

    access_token_expires = timedelta(minutes=int(auth.ACCESS_TOKEN_EXPIRE_MINUTES))
    access_token = auth.create_access_token(
        subject=user.email, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/confirm")
def confirm_email(token: str, db: Session = Depends(get_db)):
    email = auth.verify_confirmation_token(token)
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=400, detail="User not found")

    base = os.getenv("EMAIL_CONFIRM_URL", os.getenv("VITE_API_BASE", "http://localhost:8000"))
    # remove entry dev (se existir) para manter a store limpa
    try:
        pop_dev_confirmation(email)
    except Exception:
        pass

    if user.is_active:
        return RedirectResponse(url=f"{base.rstrip('/')}/auth/confirmed?status=already")

    crud.activate_user(db, user)
    return RedirectResponse(url=f"{base.rstrip('/')}/auth/confirmed?status=success")


@router.get("/confirmed")
def confirmed(status: str = "success"):
    if status == "success":
        msg = "E-mail confirmado com sucesso!"
    elif status == "already":
        msg = "Conta já confirmada."
    else:
        msg = f"Status: {status}"
    return HTMLResponse(
        f"""
        <html><head><title>Confirmação</title></head>
        <body style="font-family: Arial, sans-serif; text-align:center; padding:40px;">
          <h1>{msg}</h1>
          <p>Você pode fechar esta página e voltar ao aplicativo.</p>
        </body></html>
    """
    )


@router.post("/resend-confirmation")
def resend_confirmation(payload: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    email = payload.get("email")
    if not email:
        raise HTTPException(status_code=400, detail="Email required")
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.is_active:
        return {"message": "Account already active"}

    token = auth.create_confirmation_token(user.email)
    background_tasks.add_task(send_confirmation_email, user.email, token)
    return {"message": "Confirmation email sent"}


# --- DEV-only endpoints ---
@router.get("/dev/confirmations")
def dev_list_confirmations():
    if not (DISABLE_EMAILS or ENABLE_DEV_EMAIL_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Not found")
    return get_dev_confirmations()


@router.get("/dev/confirmations/{email}")
def dev_get_confirmation(email: str):
    if not (DISABLE_EMAILS or ENABLE_DEV_EMAIL_ENDPOINTS):
        raise HTTPException(status_code=404, detail="Not found")
    conf = get_dev_confirmations().get(email)
    if not conf:
        raise HTTPException(status_code=404, detail="Confirmation not found")
    return conf
