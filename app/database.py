import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from urllib.parse import quote_plus
from dotenv import load_dotenv

load_dotenv()

# Lê a url do env (ex: mysql+pymysql://user:pass@host:3306/db)
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./database.sqlite")

# Cria engine
# Para MySQL com pymysql não precisa do connect_args do sqlite
engine = create_engine(
    DATABASE_URL,
    pool_pre_ping=True,
    future=True,   # opcional, usa API futura do SQLAlchemy
)

SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)
Base = declarative_base()
