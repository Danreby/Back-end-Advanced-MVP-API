import os
import sys
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from passlib.context import CryptContext

from .models import Base, User

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://NeydoMVP:senha123@127.0.0.1:3306/MVPAPI?charset=utf8mb4"
)

DEFAULT_ADMIN_EMAIL = os.getenv("ADMIN_EMAIL", "admin@example.com")
DEFAULT_ADMIN_NAME = os.getenv("ADMIN_NAME", "Administrador")
DEFAULT_ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

OLD_BAD_EMAIL = "admin@catgame.local"

engine = create_engine(DATABASE_URL, future=True, pool_pre_ping=True)
Session = sessionmaker(bind=engine, autoflush=False, future=True)

pwd_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")


def seed_admin():
    print(f"[seed] Database URL: {DATABASE_URL}")
    print(f"[seed] E-mail alvo: {DEFAULT_ADMIN_EMAIL}")

    try:
        test_hash = pwd_ctx.hash("test")
        assert pwd_ctx.verify("test", test_hash)
    except Exception as e:
        print("[seed] ERRO: bcrypt não está funcionando corretamente no ambiente.")
        print("[seed] Mensagem:", e)
        print("[seed] Instale/atualize: pip install bcrypt passlib")
        sys.exit(1)

    session = Session()
    try:
        hashed = pwd_ctx.hash(DEFAULT_ADMIN_PASSWORD)

        try:
            ok = pwd_ctx.verify(DEFAULT_ADMIN_PASSWORD, hashed)
        except Exception:
            ok = False
        print(f"[seed] Hash gerado (prefixo): {hashed[:60]}... Verificação local: {'OK' if ok else 'FALHOU'}")

        user = session.query(User).filter(User.email == DEFAULT_ADMIN_EMAIL).first()
        if user:
            print(f"[seed] Usuário já existe ({DEFAULT_ADMIN_EMAIL}) — atualizando senha/nome/ativo.")
            user.hashed_password = hashed
            user.name = DEFAULT_ADMIN_NAME
            user.is_active = True
            session.commit()
            print("[seed] Atualização concluída.")
            return

        old = session.query(User).filter(User.email == OLD_BAD_EMAIL).first()
        if old:
            conflict = session.query(User).filter(User.email == DEFAULT_ADMIN_EMAIL).first()
            if conflict:
                print(f"[seed] Conflito: já existe {DEFAULT_ADMIN_EMAIL}. Atualizando apenas senha/ativo de {OLD_BAD_EMAIL}.")
                old.hashed_password = hashed
                old.name = DEFAULT_ADMIN_NAME
                old.is_active = True
            else:
                print(f"[seed] Atualizando e-mail {OLD_BAD_EMAIL} -> {DEFAULT_ADMIN_EMAIL} e atualizando senha.")
                old.email = DEFAULT_ADMIN_EMAIL
                old.hashed_password = hashed
                old.name = DEFAULT_ADMIN_NAME
                old.is_active = True
            session.commit()
            print("[seed] Atualização concluída.")
            return

        print(f"[seed] Criando novo usuário {DEFAULT_ADMIN_EMAIL}")
        new_user = User(
            email=DEFAULT_ADMIN_EMAIL,
            name=DEFAULT_ADMIN_NAME,
            hashed_password=hashed,
            is_active=True
        )
        session.add(new_user)
        session.commit()
        print("[seed] Criação concluída. Login:", DEFAULT_ADMIN_EMAIL)
        return

    except Exception as e:
        session.rollback()
        print("[seed] Erro durante o seed:", e)
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_admin()
