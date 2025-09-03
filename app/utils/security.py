# app/utils/security.py
import hashlib
from datetime import datetime, timedelta

def hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()

def token_expiration(minutes: int = 30):
    return datetime.utcnow() + timedelta(minutes=minutes)
