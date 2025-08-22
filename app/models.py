from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from .database import Base


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=False)   # muda para False até confirmar
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Produto(Base):
    __tablename__ = "product"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)   # Agora com tamanho
    desc = Column(String(255), index=True, nullable=True)

class Setor(Base):
    __tablename__ = "sector"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)   # Agora com tamanho
    desc = Column(String(255), index=True, nullable=True)