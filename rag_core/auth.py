"""Student and teacher authentication.

Passwords are bcrypt hashes. Sessions are JWTs sent as ``Authorization: Bearer``.
The role and the disabled flag always come from MongoDB, not from the token
claims alone, so disabling an account takes effect on the next request.
"""

import asyncio
import logging
import os
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from rag_core.config import DEFAULT_JWT_SECRET, jwt_secret
from rag_core.store import find_user

logger = logging.getLogger("codelens.auth")

TOKEN_TTL_DAYS = 7
_bearer = HTTPBearer(auto_error=False)


def password_rounds() -> int:
    raw = os.getenv("BCRYPT_ROUNDS", "12")
    try:
        rounds = int(raw)
    except ValueError:
        rounds = 12
    return min(max(rounds, 4), 14)


def _hash_sync(password: str) -> str:
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=password_rounds()))
    return hashed.decode("utf-8")


def _verify_sync(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


async def hash_password(password: str) -> str:
    return await asyncio.to_thread(_hash_sync, password)


async def verify_password(password: str, password_hash: str) -> bool:
    return await asyncio.to_thread(_verify_sync, password, password_hash)


def create_token(user_id: str, role: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "role": role,
        "iat": now,
        "exp": now + timedelta(days=TOKEN_TTL_DAYS),
    }
    return jwt.encode(payload, jwt_secret(), algorithm="HS256")


def decode_token(token: str) -> dict:
    return jwt.decode(token, jwt_secret(), algorithms=["HS256"])


def public_user(doc: dict) -> dict:
    return {
        "id": str(doc.get("id") or doc["_id"]),
        "name": doc["name"],
        "email": doc["email"],
        "role": doc["role"],
    }


async def current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(_bearer),
) -> dict:
    """The account behind the bearer token. Disabled accounts are rejected."""
    if creds is None or creds.scheme.lower() != "bearer" or not creds.credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    try:
        payload = decode_token(creds.credentials)
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Invalid token") from None
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = await find_user(str(user_id))
    if user is None:
        raise HTTPException(status_code=401, detail="Invalid token")
    if user.get("disabled"):
        raise HTTPException(status_code=403, detail="Account disabled")
    safe = {key: value for key, value in user.items() if key != "password_hash"}
    safe["id"] = str(safe.pop("_id"))
    return safe


async def current_teacher(user: dict = Depends(current_user)) -> dict:
    if user.get("role") != "teacher":
        raise HTTPException(status_code=403, detail="Teacher access required")
    return user


def warn_default_secret() -> None:
    if jwt_secret() == DEFAULT_JWT_SECRET:
        logger.warning(
            "JWT_SECRET is still the default. Set a real secret before sharing this API."
        )
