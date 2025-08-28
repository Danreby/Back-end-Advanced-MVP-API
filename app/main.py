import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import engine, Base
from .routers import auth_router, users_router, giantbomb_router, games_router, reviews_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FastAPI + MySQL + JWT")

# --- CORS ---
origins = [
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- ROTAS / Routers ---
app.include_router(auth_router.router)
app.include_router(users_router.router)
app.include_router(giantbomb_router.router)
app.include_router(games_router.router)
app.include_router(reviews_router.router)

# --- Static / Avatars ---

BASE_DIR = Path(__file__).resolve().parent.parent 
STATIC_DIR = BASE_DIR / "static"
AVATAR_DIR = STATIC_DIR / "avatars"
AVATAR_DIR.mkdir(parents=True, exist_ok=True)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/ping")
def pong():
    return {"msg": "pong"}
