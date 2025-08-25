# app/models.py
from sqlalchemy import (
    Column, Integer, String, Boolean, DateTime, ForeignKey, Text,
    UniqueConstraint
)
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from .database import Base

class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=True)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # relacionamentos
    games = relationship("Game", back_populates="user", cascade="all,delete-orphan")
    reviews = relationship("Review", back_populates="user", cascade="all,delete-orphan")


class Game(Base):
    __tablename__ = "games"  # plural é comum, mas use o que preferir

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    # se o jogo foi importado da GiantBomb, guarde o GUID (ex: "3030-4725")
    external_guid = Column(String(100), nullable=True, index=True)
    # capa/thumbnail principal (URL)
    cover_url = Column(String(1000), nullable=True)
    # descrição local (curta); para textos maiores use Text
    description = Column(Text, nullable=True)
    # referência ao usuário dono (se cada usuário tem seu catálogo privado)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    # metadados do catálogo do usuário
    status = Column(String(50), nullable=False, default="Wishlist")  # ex: Wishlist, Playing, Played
    start_date = Column(DateTime(timezone=True), nullable=True)
    finish_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # relacionamentos
    user = relationship("User", back_populates="games")
    reviews = relationship("Review", back_populates="game", cascade="all,delete-orphan")


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        # garante que um usuário só tenha uma review por jogo
        UniqueConstraint("user_id", "game_id", name="uq_user_game_review"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)

    # avaliação/nota: int 0-10 (você pode usar Float se preferir)
    rating = Column(Integer, nullable=True)  # validar 0-10 no schema/endpoint

    # texto da review
    review_text = Column(Text, nullable=True)

    # se quiser permitir reviews privadas
    is_public = Column(Boolean, default=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    # relacionamentos
    user = relationship("User", back_populates="reviews")
    game = relationship("Game", back_populates="reviews")
