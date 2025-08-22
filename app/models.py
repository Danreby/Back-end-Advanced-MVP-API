from sqlalchemy import Column, Integer, String
from app.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)   # Agora com tamanho
    email = Column(String(255), unique=True, index=True, nullable=False)
    password = Column(String(255), nullable=False)

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