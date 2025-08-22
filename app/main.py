from fastapi import FastAPI, Depends
from .database import engine, Base
from .routers import auth_router
from .auth import get_current_user


# cria tabelas automaticamente (apenas para dev; em produção use migrations como alembic)
Base.metadata.create_all(bind=engine)


app = FastAPI(title="FastAPI + MySQL + JWT")


app.include_router(auth_router.router)


@app.get("/ping")
def pong():
    return {"msg": "pong"}


@app.get('/users/me')
def read_users_me(current_user = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "name": current_user.name}