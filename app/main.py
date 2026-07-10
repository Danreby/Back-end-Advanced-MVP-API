import os
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.security.api_key import APIKeyHeader
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import JSONResponse

from .database import engine, Base
from .routers import auth_router, users_router, giantbomb_router, games_router, reviews_router

Base.metadata.create_all(bind=engine)

ENABLE_DOCS = os.getenv("ENABLE_DOCS", "true").lower() in ("1", "true", "yes")
DOCS_API_KEY = os.getenv("DOCS_API_KEY")

openapi_tags = [
    {
        "name": "auth",
        "description": "Registro de conta, login e confirmação de e-mail.",
    },
    {
        "name": "users",
        "description": "Perfil do usuário autenticado, busca de usuários, sistema de amizades e sessões de jogo.",
    },
    {
        "name": "games",
        "description": "Catálogo pessoal de jogos: criação, listagem, atualização, status e sessões.",
    },
    {
        "name": "reviews",
        "description": "Reviews e avaliações de jogos — criação, edição, remoção e listagens públicas.",
    },
    {
        "name": "giantbomb",
        "description": "Busca e detalhes de jogos via API externa do GiantBomb.",
    },
    {
        "name": "dev",
        "description": "⚠️ Endpoints disponíveis apenas em modo de desenvolvimento (`DISABLE_EMAILS=True`).",
    },
]

_swagger_params = {
    "defaultModelsExpandDepth": -1,
    "displayRequestDuration": True,
    "filter": True,
    "persistAuthorization": True,
    "tryItOutEnabled": True,
}

_app_meta = dict(
    title="GameLink API",
    description=(
        "API do **GameLink** — plataforma de catálogo de jogos com reviews públicas e sistema de amizades.\n\n"
        "### Autenticação\n"
        "A maioria dos endpoints exige um token JWT via `Authorization: Bearer <token>`. "
        "Obtenha o token em **POST /auth/login** e use o botão **Authorize** acima."
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

if DOCS_API_KEY:
    app = FastAPI(**_app_meta, docs_url=None, redoc_url=None, openapi_url=None)
elif ENABLE_DOCS:
    app = FastAPI(
        **_app_meta,
        docs_url="/",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        swagger_ui_parameters=_swagger_params,
    )
else:
    app = FastAPI(**_app_meta, docs_url=None, redoc_url=None, openapi_url=None)

# --- CORS ---
_cors_env = os.getenv("CORS_ORIGINS", "")
if _cors_env:
    origins = [o.strip() for o in _cors_env.split(",") if o.strip()]
else:
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

# --- ROUTERS ---
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


@app.get("/ping", tags=["auth"], summary="Health check", include_in_schema=False)
def pong():
    return {"msg": "pong"}


if DOCS_API_KEY:
    api_key_header = APIKeyHeader(name="X-Docs-Key", auto_error=False)

    def check_docs_key(api_key: Optional[str] = Depends(api_key_header)):
        if api_key != DOCS_API_KEY:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    @app.get("/openapi.json", dependencies=[Depends(check_docs_key)], include_in_schema=False)
    def protected_openapi():
        return JSONResponse(app.openapi())

    @app.get("/", dependencies=[Depends(check_docs_key)], include_in_schema=False)
    def protected_swagger_root():
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title="GameLink API Docs",
            swagger_ui_parameters=_swagger_params,
        )

elif ENABLE_DOCS:
    pass
