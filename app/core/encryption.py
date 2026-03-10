import logging
import sys

from cryptography.fernet import Fernet, InvalidToken

from app.config import settings

logger = logging.getLogger(__name__)

_fernet: Fernet | None = None


def _get_fernet() -> Fernet:
    global _fernet
    if _fernet is None:
        key = settings.llm_encryption_key
        if not key:
            msg = (
                "\n\n"
                "===== ERRO FATAL =====\n"
                "LLM_ENCRYPTION_KEY nao esta configurada.\n"
                "O sistema nao pode iniciar sem ela.\n"
                "Gere uma chave com:\n"
                "  python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\"\n"
                "e adicione ao .env\n"
                "======================\n"
            )
            logger.critical(msg)
            raise SystemExit(msg)
        _fernet = Fernet(key.encode())
    return _fernet


def validate_encryption_key():
    """Valida que LLM_ENCRYPTION_KEY esta configurada. Chamar na inicializacao."""
    _get_fernet()


def encrypt_api_key(plain_key: str) -> str:
    return _get_fernet().encrypt(plain_key.encode()).decode()


def decrypt_api_key(encrypted_key: str) -> str:
    try:
        return _get_fernet().decrypt(encrypted_key.encode()).decode()
    except InvalidToken:
        logger.error("Falha ao descriptografar API key — chave de criptografia incorreta?")
        raise ValueError("Falha ao descriptografar API key")


def mask_api_key(key: str | None) -> str:
    if not key:
        return ""
    if len(key) <= 4:
        return "****"
    return f"...{key[-4:]}"
