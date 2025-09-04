import os
import logging
from dotenv import load_dotenv
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from fastapi import HTTPException
from app.auth import create_confirmation_token
from typing import Optional

load_dotenv()
logger = logging.getLogger("app.mail")

def _env_bool(key: str, default: str = "False") -> bool:
    return os.getenv(key, default).lower() in ("true", "1", "yes")

MAIL_USERNAME = os.getenv("MAIL_USERNAME")
MAIL_PASSWORD = os.getenv("MAIL_PASSWORD")
MAIL_FROM = os.getenv("MAIL_FROM", MAIL_USERNAME)
MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "API")
MAIL_SERVER = os.getenv("MAIL_SERVER", "smtp.gmail.com")
MAIL_PORT = int(os.getenv("MAIL_PORT", 587))
MAIL_USE_TLS = _env_bool("MAIL_USE_TLS", "True")
MAIL_USE_SSL = _env_bool("MAIL_USE_SSL", "False")
DISABLE_EMAILS = _env_bool("DISABLE_EMAILS", "False")
ENABLE_DEV_EMAIL_ENDPOINTS = _env_bool("ENABLE_DEV_EMAIL_ENDPOINTS", "True")

conf = ConnectionConfig(
    MAIL_USERNAME=MAIL_USERNAME,
    MAIL_PASSWORD=MAIL_PASSWORD,
    MAIL_FROM=MAIL_FROM,
    MAIL_FROM_NAME=MAIL_FROM_NAME,
    MAIL_SERVER=MAIL_SERVER,
    MAIL_PORT=MAIL_PORT,
    MAIL_STARTTLS=MAIL_USE_TLS,
    MAIL_SSL_TLS=MAIL_USE_SSL,
    USE_CREDENTIALS=True,
    VALIDATE_CERTS=True,
    TEMPLATE_FOLDER="app/templates"
)

DEV_CONFIRMATIONS: dict[str, dict] = {}


async def send_email(subject: str, recipients: list[str], body: str, subtype: MessageType = MessageType.plain) -> bool:
    if DISABLE_EMAILS:
        logger.info("Envio de e-mail desabilitado (DISABLE_EMAILS=True). Simulando envio para %s", recipients)
        logger.debug("Email subject=%s body=%s", subject, body)
        return True

    message = MessageSchema(subject=subject, recipients=recipients, body=body, subtype=subtype)
    fm = FastMail(conf)
    try:
        await fm.send_message(message)
        logger.info("E-mail enviado para %s (subject=%s)", recipients, subject)
        return True
    except Exception as exc:
        logger.exception("Falha ao enviar e-mail para %s: %s", recipients, exc)
        return False


async def send_confirmation_email(user_email: str, token: Optional[str] = None) -> str:
    if token is None:
        token = create_confirmation_token(user_email)

    base = os.getenv("EMAIL_CONFIRM_URL", os.getenv("VITE_API_BASE", "http://localhost:8000")).rstrip("/")
    confirmation_url = f"{base}/auth/confirm?token={token}"

    logger.info("Confirmation URL for %s: %s", user_email, confirmation_url)
    print(f"Confirme sua conta acessando: {confirmation_url}")

    if DISABLE_EMAILS:
        DEV_CONFIRMATIONS[user_email] = {
            "token": token,
            "url": confirmation_url,
            "created_at": __import__("time").time()
        }
        try:
            os.makedirs("dev", exist_ok=True)
            with open("dev/confirmation_links.log", "a", encoding="utf-8") as f:
                f.write(f"{user_email} {confirmation_url}\n")
        except Exception:
            logger.exception("Não consegui gravar dev/confirmation_links.log")
        return confirmation_url

    subject = "Confirme sua conta"
    recipients = [user_email]
    body = f"Olá,\n\nPor favor confirme sua conta clicando no link a seguir:\n\n{confirmation_url}\n\nObrigado!"
    sent = await send_email(subject=subject, recipients=recipients, body=body, subtype=MessageType.plain)
    if not sent:
        logger.warning("Falha ao enviar e-mail de confirmação para %s (mas link retornado).", user_email)
    return confirmation_url


def get_dev_confirmations() -> dict:
    return DEV_CONFIRMATIONS

def pop_dev_confirmation(email: str):
    return DEV_CONFIRMATIONS.pop(email, None)
