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

    games = relationship("Game", back_populates="user", cascade="all,delete-orphan")
    reviews = relationship("Review", back_populates="user", cascade="all,delete-orphan")


class Game(Base):
    __tablename__ = "games"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    external_guid = Column(String(100), nullable=True, index=True)
    cover_url = Column(String(1000), nullable=True)
    description = Column(Text, nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)

    status = Column(String(50), nullable=False, default="Wishlist")
    start_date = Column(DateTime(timezone=True), nullable=True)
    finish_date = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", back_populates="games")
    reviews = relationship("Review", back_populates="game", cascade="all,delete-orphan")


class Review(Base):
    __tablename__ = "reviews"
    __table_args__ = (
        UniqueConstraint("user_id", "game_id", name="uq_user_game_review"),
    )

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    rating = Column(Integer, nullable=True)
    review_text = Column(Text, nullable=True)
    is_public = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", back_populates="reviews")
    game = relationship("Game", back_populates="reviews")

class Section(Base):
    __tablename__ = "sections"
    __table_args__ = (
        UniqueConstraint("user_id", "game_id", name="uq_user_game_section"),
    )

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255))
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    game_id = Column(Integer, ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)