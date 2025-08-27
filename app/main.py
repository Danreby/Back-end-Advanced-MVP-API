import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .database import engine, Base
from .routers import auth_router, users_router, giantbomb_router, games_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="FastAPI + MySQL + JWT")

app.include_router(giantbomb_router.router)
app.include_router(games_router.router)

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
# -------------- end CORS --------------

app.include_router(auth_router.router)
app.include_router(users_router.router)

AVATAR_DIR = "static/avatars"
os.makedirs(AVATAR_DIR, exist_ok=True)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/ping")
def pong():
    return {"msg": "pong"}
