import logging

import httpx
from jose import JWTError, jwt

from app.config import settings

logger = logging.getLogger(__name__)

_jwks_cache: dict | None = None


def _get_jwks() -> dict | None:
    """Busca e cacheia as chaves publicas JWKS do Supabase."""
    global _jwks_cache
    if _jwks_cache:
        return _jwks_cache
    try:
        resp = httpx.get(
            f"{settings.supabase_url}/auth/v1/.well-known/jwks.json",
            headers={"apikey": settings.supabase_service_role_key},
            timeout=10,
        )
        resp.raise_for_status()
        jwks = resp.json()
        if jwks.get("keys"):
            _jwks_cache = jwks["keys"][0]
            return _jwks_cache
    except Exception as e:
        logger.error("Erro ao buscar JWKS do Supabase: %s", e)
    return None


def decode_supabase_jwt(token: str) -> dict | None:
    """Decodifica e valida um JWT emitido pelo Supabase Auth."""
    key = _get_jwks()
    if not key:
        logger.error("JWKS nao disponivel")
        return None
    try:
        payload = jwt.decode(
            token,
            key,
            algorithms=["ES256"],
            options={"verify_aud": False},
        )
        return payload
    except JWTError as e:
        logger.debug("JWT decode error: %s", e)
        return None
