"""Refresh token management — rotação, revogação e detecção de replay."""
import hashlib
import secrets
from datetime import datetime, timedelta

from sqlalchemy import text
from sqlalchemy.orm import Session

TOKEN_BYTES = 32
TOKEN_EXPIRY_DAYS = 7


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def create_refresh_token(
    db: Session,
    user_id: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> str:
    """Cria novo refresh token para o usuario. Retorna o token plain-text."""
    token = secrets.token_urlsafe(TOKEN_BYTES)
    token_hash = _hash_token(token)
    expires_at = datetime.utcnow() + timedelta(days=TOKEN_EXPIRY_DAYS)

    db.execute(
        text("""
            INSERT INTO refresh_tokens (token_hash, user_id, expires_at, ip_address, user_agent)
            VALUES (:hash, :uid, :exp, :ip, :ua)
        """),
        {
            "hash": token_hash,
            "uid": user_id,
            "exp": expires_at,
            "ip": ip_address,
            "ua": user_agent,
        },
    )
    db.commit()
    return token


def validate_and_rotate(
    db: Session,
    token: str,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> tuple[str, str]:
    """Valida refresh token e emite novo (rotação). Retorna (new_token, user_id).

    Raises ValueError se token inválido, expirado ou já usado (replay).
    """
    token_hash = _hash_token(token)

    row = db.execute(
        text("""
            SELECT user_id, expires_at, revoked_at, used_at, family_id
            FROM refresh_tokens
            WHERE token_hash = :hash
        """),
        {"hash": token_hash},
    ).mappings().first()

    if not row:
        raise ValueError("Token não encontrado")

    # Token já foi usado → possível replay attack → revogar toda a família
    if row["used_at"]:
        family_id = row.get("family_id") or token_hash
        db.execute(
            text("""
                UPDATE refresh_tokens
                SET revoked_at = now()
                WHERE (family_id = :fam OR token_hash = :fam)
                  AND revoked_at IS NULL
            """),
            {"fam": family_id},
        )
        db.commit()
        raise ValueError("Replay detectado — família revogada")

    if row["revoked_at"]:
        raise ValueError("Token revogado")

    if row["expires_at"] < datetime.utcnow():
        raise ValueError("Token expirado")

    # Marcar token atual como usado
    family_id = row.get("family_id") or token_hash
    db.execute(
        text("UPDATE refresh_tokens SET used_at = now() WHERE token_hash = :hash"),
        {"hash": token_hash},
    )

    # Criar novo token na mesma família
    new_token = secrets.token_urlsafe(TOKEN_BYTES)
    new_hash = _hash_token(new_token)
    expires_at = datetime.utcnow() + timedelta(days=TOKEN_EXPIRY_DAYS)

    db.execute(
        text("""
            INSERT INTO refresh_tokens (token_hash, user_id, expires_at, ip_address, user_agent, family_id)
            VALUES (:hash, :uid, :exp, :ip, :ua, :fam)
        """),
        {
            "hash": new_hash,
            "uid": row["user_id"],
            "exp": expires_at,
            "ip": ip_address,
            "ua": user_agent,
            "fam": family_id,
        },
    )
    db.commit()
    return new_token, row["user_id"]


def revoke_token(db: Session, token: str) -> None:
    """Revoga um refresh token específico."""
    token_hash = _hash_token(token)
    db.execute(
        text("UPDATE refresh_tokens SET revoked_at = now() WHERE token_hash = :hash"),
        {"hash": token_hash},
    )
    db.commit()


def revoke_all_user_tokens(db: Session, user_id: str) -> int:
    """Revoga todos os refresh tokens de um usuario. Retorna quantidade revogada."""
    result = db.execute(
        text("""
            UPDATE refresh_tokens
            SET revoked_at = now()
            WHERE user_id = :uid AND revoked_at IS NULL
        """),
        {"uid": user_id},
    )
    db.commit()
    return result.rowcount
