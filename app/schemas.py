from pydantic import BaseModel, EmailStr
from typing import Optional


class UserCreate(BaseModel):
    email: EmailStr
    password: str
    name: Optional[str] = None


class UserOut(BaseModel):
    id: int
    email: EmailStr
    name: Optional[str]
    is_active: bool


class Config:
    orm_mode = True


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None