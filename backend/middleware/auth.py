"""
fynd(cars) — Supabase JWT Auth Middleware
Verifies JWT from Supabase Auth. Extracts user ID and role.
Role is read ONLY from app_metadata (admin-controlled), never user_metadata (user-editable).
"""

import os
import logging
from typing import Optional
from fastapi import Header, HTTPException, Depends, status

logger = logging.getLogger("fynd(cars)_api")

SUPABASE_JWT_SECRET = os.getenv("SUPABASE_JWT_SECRET", "")


def get_current_user(authorization: Optional[str] = Header(None)) -> dict:
    """
    FastAPI dependency → { "id": uuid, "role": str, "email": str }
    Verifies Supabase JWT when SUPABASE_JWT_SECRET is set.
    In dev without the secret, accepts 'Bearer demo-<role>' tokens for local testing.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing Authorization: Bearer <token>")

    token = authorization.split(" ", 1)[1].strip()

    if SUPABASE_JWT_SECRET:
        try:
            import jwt
            payload = jwt.decode(token, SUPABASE_JWT_SECRET, algorithms=["HS256"], options={"verify_aud": False})
        except Exception as e:
            logger.warning("JWT verification failed: %s", e)
            raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid or expired token: {e}")
    else:
        # Dev mode: decode without verification OR accept simple demo tokens
        try:
            import jwt
            payload = jwt.decode(token, options={"verify_signature": False})
        except Exception:
            # Simple demo tokens for local curl testing
            role = "admin" if "admin" in token else "seller" if "seller" in token else "buyer"
            return {"id": f"demo-{role}-id", "role": role, "email": f"{role}@fynd(cars).dev"}

    # Role: ONLY from app_metadata — user_metadata is user-editable and unsafe for authz
    role = (payload.get("app_metadata") or {}).get("role") or payload.get("role") or "buyer"

    return {
        "id": payload.get("sub", ""),
        "role": role,
        "email": payload.get("email", ""),
    }


def get_optional_user(authorization: Optional[str] = Header(None)) -> Optional[dict]:
    """
    Like get_current_user, but returns None instead of raising when the
    request is unauthenticated. For endpoints usable by both anon and
    logged-in users (e.g. logging a listing view).
    """
    if not authorization or not authorization.startswith("Bearer "):
        return None
    try:
        return get_current_user(authorization)
    except HTTPException:
        return None


def require_role(allowed_roles: list[str]):
    """
    RBAC dependency factory.
    Usage: dependencies=[Depends(require_role(["admin"]))]
    Or:    user: dict = Depends(require_role(["seller", "admin"]))
    """
    def checker(user: dict = Depends(get_current_user)) -> dict:
        if user.get("role") not in allowed_roles:
            raise HTTPException(
                status.HTTP_403_FORBIDDEN,
                f"Requires role: {allowed_roles}. Your role: {user.get('role')}",
            )
        return user
    return checker
