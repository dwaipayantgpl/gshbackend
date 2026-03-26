# app/auth/logic/tokens.py
import os
from datetime import datetime, timedelta, timezone

from dotenv import load_dotenv
from jose import jwt

load_dotenv()

JWT_SECRET = os.getenv("JWT_SECRET")
JWT_ALG = os.getenv("JWT_ALG", "HS256")
JWT_EXPIRES_MIN = int(os.getenv("JWT_EXPIRES_MIN", "1440"))


def create_access_token(*, sub: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": sub,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=JWT_EXPIRES_MIN)).timestamp()),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)


def decode_access_token(token: str) -> dict:
    # raises JWTError on invalid/expired token
    return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
