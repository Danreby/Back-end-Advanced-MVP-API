# test_conn.py
import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

load_dotenv()  # carrega .env na raiz

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise SystemExit(
        "ERRO: DATABASE_URL não encontrada. Crie um .env com DATABASE_URL=... "
        "ou exporte a variável de ambiente antes de rodar."
    )

print("Usando DATABASE_URL:", DATABASE_URL)

try:
    engine = create_engine(DATABASE_URL, pool_pre_ping=True)
    with engine.connect() as conn:
        r = conn.execute(text("SELECT VERSION();"))
        version = r.scalar()
        print("Conectado com sucesso — MySQL version:", version)
except SQLAlchemyError as e:
    print("Erro ao conectar ao banco:", e)
    raise
