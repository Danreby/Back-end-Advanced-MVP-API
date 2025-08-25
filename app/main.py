from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import auth_router
from .auth import get_current_user
# em app/main.py (exemplo)
from app.routers import giantbomb_router

# cria tabelas automaticamente (apenas para dev; em produção use migrations como alembic)
Base.metadata.create_all(bind=engine)

app = FastAPI(title="FastAPI + MySQL + JWT")

app.include_router(giantbomb_router.router)
# --- CORS ---
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",     # opcional: outras portas que você use
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,       # lista explícita de orígens em dev
    allow_credentials=True,      # True se você enviar cookies/credentials do client
    allow_methods=["*"],         # permite GET, POST, OPTIONS, PUT, DELETE...
    allow_headers=["*"],         # permite Content-Type, Authorization etc.
)
# -------------- end CORS --------------

app.include_router(auth_router.router)

@app.get("/ping")
def pong():
    return {"msg": "pong"}

@app.get('/users/me')
def read_users_me(current_user = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "name": current_user.name}
