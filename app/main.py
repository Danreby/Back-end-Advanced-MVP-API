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

if not ENABLE_DOCS or DOCS_API_KEY:
    app = FastAPI(title="MVP API", docs_url=None, redoc_url=None, openapi_url=None)
else:
    app = FastAPI(
        title="MVP API",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
    )

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


@app.get("/ping")
def pong():
    return {"msg": "pong"}


# --- Swagger protegido ---
if DOCS_API_KEY:
    api_key_header = APIKeyHeader(name="X-Docs-Key", auto_error=False)

    def check_docs_key(api_key: Optional[str] = Depends(api_key_header)):
        if api_key != DOCS_API_KEY:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    @app.get("/openapi.json", dependencies=[Depends(check_docs_key)])
    def protected_openapi():
        return JSONResponse(app.openapi())

    @app.get("/docs", dependencies=[Depends(check_docs_key)])
    def protected_swagger():
        return get_swagger_ui_html(
            openapi_url="/openapi.json",
            title="Docs (protegido)",
            swagger_ui_parameters={
                "defaultModelsExpandDepth": -1,
                "displayRequestDuration": True,
            },
        )

elif ENABLE_DOCS:
    pass
