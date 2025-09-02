from pydantic import BaseModel, EmailStr, Field, conint, ConfigDict
from typing import Optional, List
from datetime import datetime


# --- Users / Auth ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class UserUpdate(BaseModel):
    name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None  


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str] = None
    bio: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    created_at: Optional[datetime] = None
    games_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class ChangePassword(BaseModel):
    old_password: str
    new_password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


# --- Reviews ---
class ReviewUser(BaseModel):
    id: int
    name: Optional[str] = None
    avatar_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReviewGame(BaseModel):
    id: int
    name: str
    cover_url: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ReviewCreate(BaseModel):
    rating: conint(ge=0, le=10)  # obrigatório na criação
    review_text: Optional[str] = None
    is_public: bool = True


class ReviewUpdate(BaseModel):
    # todos opcionais → permite atualizar só a nota, só o texto, ou ambos
    rating: Optional[conint(ge=0, le=10)] = None
    review_text: Optional[str] = None
    is_public: Optional[bool] = None


class ReviewOut(BaseModel):
    id: int
    user_id: int
    game_id: int
    rating: Optional[int]
    review_text: Optional[str]
    is_public: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    user: Optional[ReviewUser] = None
    game: Optional[ReviewGame] = None

    model_config = ConfigDict(from_attributes=True)


# --- Games ---
class GameCreate(BaseModel):
    name: str = Field(..., max_length=255)
    external_guid: Optional[str] = None
    cover_url: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field("Wishlist", max_length=50)
    start_date: Optional[datetime] = None
    finish_date: Optional[datetime] = None


class GameUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    cover_url: Optional[str] = None
    description: Optional[str] = None
    status: Optional[str] = Field(None, max_length=50)
    start_date: Optional[datetime] = None
    finish_date: Optional[datetime] = None


class GameOut(BaseModel):
    id: int
    name: str
    external_guid: Optional[str]
    cover_url: Optional[str]
    description: Optional[str]
    status: str
    start_date: Optional[datetime]
    finish_date: Optional[datetime]
    user_id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class GameWithRating(GameOut):
    avg_rating: Optional[float] = None
    reviews_count: int = 0

    model_config = ConfigDict(from_attributes=True)


class GameWithReviews(BaseModel):
    id: int
    name: str
    avg_rating: Optional[float] = None
    reviews: List[ReviewOut] = Field(default_factory=list)
    reviews_count: int = 0

    model_config = ConfigDict(from_attributes=True)


# --- Pagination wrappers ---
class PaginatedGames(BaseModel):
    total: int
    items: List[GameOut] = Field(default_factory=list)


class PaginatedReviews(BaseModel):
    total: int
    items: List[ReviewOut] = Field(default_factory=list)

# --- Reutilizáveis / base ---
class ReviewBase(BaseModel):
    rating: Optional[int] = Field(None, ge=0, le=10, description="Nota (0-10)")
    review_text: Optional[str] = Field(None, max_length=5000, description="Texto da review")
    is_public: Optional[bool] = Field(True, description="Se a review é pública")

    class Config:
        orm_mode = True


# --- Payload para upsert (criar ou atualizar em uma chamada) ---
class ReviewUpsert(ReviewBase):
    game_id: Optional[int] = Field(None, description="ID interno do game (opcional se usar external_guid)")
    external_guid: Optional[str] = Field(None, description="GUID externo do jogo (ex.: GiantBomb)")
    name: Optional[str] = Field(None, description="Nome do jogo (opcional; só usado se for criar game mínimo)")

    class Config:
        orm_mode = True


# --- Payload leve para autosave (pode ser um subset do upsert) ---
class ReviewAutoSave(BaseModel):
    game_id: Optional[int] = Field(None, description="ID do jogo")
    external_guid: Optional[str] = Field(None, description="GUID externo do jogo")
    rating: Optional[int] = Field(None, ge=0, le=10, description="Nota (0-10)")
    review_text: Optional[str] = Field(None, max_length=5000, description="Texto da review")
    is_public: Optional[bool] = Field(True, description="Se a review é pública")
    name: Optional[str] = Field(None, description="Nome do jogo (opcional)")

    class Config:
        orm_mode = True
