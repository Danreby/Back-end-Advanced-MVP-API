# app/schemas.py (corrigido — coloque isto no seu arquivo)
from pydantic import BaseModel, EmailStr, Field, conint, ConfigDict
from typing import Optional, List
from datetime import datetime

# --- Users / Auth ---
class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None

class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str]
    is_active: bool
    model_config = ConfigDict(from_attributes=True)

class Token(BaseModel):
    access_token: str
    token_type: str

class TokenData(BaseModel):
    email: Optional[str] = None

# --- Game ---
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
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)

class GameWithRating(GameOut):
    avg_rating: Optional[float] = None
    reviews_count: int = 0
    model_config = ConfigDict(from_attributes=True)


# --- Review (mover para cima para evitar NameError) ---
class ReviewCreate(BaseModel):
    rating: Optional[conint(ge=0, le=10)] = None
    review_text: Optional[str] = None
    is_public: Optional[bool] = True

class ReviewUpdate(BaseModel):
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
    created_at: Optional[datetime]
    updated_at: Optional[datetime]
    model_config = ConfigDict(from_attributes=True)


# --- Game with reviews (agora que ReviewOut já existe) ---
class GameWithReviews(BaseModel):
    id: int
    name: str
    avg_rating: Optional[float] = None
    reviews: List[ReviewOut] = []
    reviews_count: int = 0
    model_config = ConfigDict(from_attributes=True)


# --- Pagination wrappers ---
class PaginatedGames(BaseModel):
    total: int
    items: List[GameOut]

class PaginatedReviews(BaseModel):
    total: int
    items: List[ReviewOut]
