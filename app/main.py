from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from .database import engine, Base
from .routers import auth_router
from .auth import get_current_user
from app.routers import giantbomb_router
from app.routers import games_router

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

@app.get("/ping")
def pong():
    return {"msg": "pong"}

@app.get('/users/me')
def read_users_me(current_user = Depends(get_current_user)):
    return {"id": current_user.id, "email": current_user.email, "name": current_user.name}
