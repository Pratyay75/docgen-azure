# backend/app/auth.py
import os
import time
from typing import Optional, Dict, Any

import jwt
from fastapi import HTTPException, Header, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.database import find_by_id  # ensure this path matches your project layout

# Settings (env fallbacks)
JWT_SECRET = os.getenv("JWT_SECRET", "dev-secret-change-me")
JWT_ALGORITHM = "HS256"
TOKEN_EXP_SECONDS = int(os.getenv("TOKEN_EXP_SECONDS", "86400"))  # default 1 day

bearer_scheme = HTTPBearer(auto_error=False)


def create_token(user: Any) -> str:
    """
    Create a JWT token whose subject (sub) is the user's id.
    Accepts either:
      - user dict with 'id' or 'user_id' key
      - a plain string user id
    """
    # get user id from different possible shapes
    if isinstance(user, dict):
        user_id = user.get("id") or user.get("user_id") or user.get("sub")
    else:
        user_id = user

    if not user_id:
        raise ValueError("create_token: user id not provided")

    now = int(time.time())
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + TOKEN_EXP_SECONDS,
    }
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
    # pyjwt returns str in v2+, bytes in older — normalize to str
    if isinstance(token, bytes):
        token = token.decode("utf-8")
    return token


def _raise_401(detail: str = "Unauthorized"):
    raise HTTPException(status_code=401, detail=detail)


def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme)):
    """
    FastAPI dependency to get current user from Authorization: Bearer <token>.
    Accepts tokens with 'sub' (preferred) OR 'user_id' or 'id' in payload.
    """
    if not credentials or not credentials.credentials:
        _raise_401("Missing Authorization token")

    token = credentials.credentials
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        _raise_401("Token expired")
    except jwt.InvalidTokenError:
        _raise_401("Invalid token")

    # Accept multiple possible names for the subject:
    user_id = payload.get("sub") or payload.get("user_id") or payload.get("id")
    if not user_id:
        # helpful debug message (returned to client)
        _raise_401("Token missing subject (sub/user_id)")

    # Load user from DB (assuming find_by_id returns None if not found)
    user = find_by_id("users", str(user_id))
    if not user:
        _raise_401("User not found for token subject")

    # Optionally attach token payload into user object for later usage
    user["_token_payload"] = payload
    return user


def require_role(roles: list):
    """
    Factory: returns a dependency that asserts the user has one of the given roles.
    Usage: Depends(require_role(['admin', 'superadmin']))
    """
    def _dep(user = Depends(get_current_user)):
        if not user:
            _raise_401("Unauthorized")
        if user.get("role") not in roles:
            raise HTTPException(status_code=403, detail="Insufficient role")
        return user
    return _dep
