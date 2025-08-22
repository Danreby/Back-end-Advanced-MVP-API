from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from . import models
from .database import engine
from .routes import router as api_router

# cria tabelas automaticamente (apenas para dev)
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="My FastAPI API")

# Habilita CORS para o front local (ajuste conforme seu front)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api")

@app.get("/")
async def root():
    return {"message": "API rodando 🚀"}
