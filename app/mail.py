import os
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from dotenv import load_dotenv

load_dotenv()

conf = ConnectionConfig(
    MAIL_USERNAME = os.getenv("MAIL_USERNAME"),
    MAIL_PASSWORD = os.getenv("MAIL_PASSWORD"),
    MAIL_FROM = os.getenv("MAIL_FROM"),
    MAIL_FROM_NAME = os.getenv("MAIL_FROM_NAME", "API"),
    MAIL_SERVER = os.getenv("MAIL_SERVER"),
    MAIL_PORT = int(os.getenv("MAIL_PORT", 587)),
    MAIL_TLS = os.getenv("MAIL_USE_TLS", "True").lower() in ("true", "1", "yes"),
    MAIL_SSL = os.getenv("MAIL_USE_SSL", "False").lower() in ("true", "1", "yes"),
    USE_CREDENTIALS = True,
    TEMPLATE_FOLDER = "app/templates"
)

async def send_email(subject: str, recipients: list[str], body: str, subtype: MessageType = MessageType.plain):
    """
    Envia um email simples (texto). recipients deve ser lista, ex: ["user@example.com"]
    """
    message = MessageSchema(
        subject=subject,
        recipients=recipients,
        body=body,
        subtype=subtype
    )
    fm = FastMail(conf)
    await fm.send_message(message)
