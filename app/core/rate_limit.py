"""Rate limiting centralizado usando slowapi."""
from slowapi import Limiter
from slowapi.util import get_remote_address

# Limiter global — usa IP como key padrão
limiter = Limiter(key_func=get_remote_address)

# Constantes de limite por categoria
AUTH_LIMIT = "10/minute"
REGISTER_LIMIT = "5/minute"
ENTERPRISE_LIMIT = "10/minute"
ASK_LIMIT = "60/minute"
INGEST_LIMIT = "10/minute"
DEFAULT_LIMIT = "120/minute"
