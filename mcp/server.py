"""MCP Server — expoe tools do Memora para o Claude Code via HTTP."""

import hashlib
import logging
import secrets
import uuid

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_session, require_role
from app.models.user import User

from mcp.tools.search_code import search_similar_code
from mcp.tools.get_rules import get_business_rules
from mcp.tools.get_patterns import get_team_patterns
from mcp.tools.get_decisions import get_architecture_decisions
from mcp.tools.get_env_vars import get_environment_context
from mcp.tools.analyze_impact import analyze_change_impact

router = APIRouter()
logger = logging.getLogger(__name__)

MCP_TOOLS = [
    {
        "name": "search_similar_code",
        "description": "Busca codigo similar ja existente no sistema Memora para evitar duplicacao",
        "parameters": {
            "query": {"type": "string", "required": True, "description": "Descricao do que precisa implementar"},
            "repo_name": {"type": "string", "required": False, "description": "Limitar a um repositorio"},
            "top_k": {"type": "integer", "required": False, "default": 5, "description": "Numero de resultados"},
        },
    },
    {
        "name": "get_business_rules",
        "description": "Busca regras de negocio relevantes para o contexto de desenvolvimento",
        "parameters": {
            "context": {"type": "string", "required": True, "description": "Descricao do que esta sendo implementado"},
            "rule_types": {"type": "array", "required": False, "description": "Filtrar por tipo"},
            "repo_name": {"type": "string", "required": False},
        },
    },
    {
        "name": "get_team_patterns",
        "description": "Busca padroes e convencoes de codigo estabelecidos pelo time",
        "parameters": {
            "context": {"type": "string", "required": True},
            "language": {"type": "string", "required": False, "description": "python|javascript|typescript"},
        },
    },
    {
        "name": "get_architecture_decisions",
        "description": "Busca decisoes arquiteturais anteriores relacionadas ao contexto",
        "parameters": {
            "context": {"type": "string", "required": True},
            "repo_name": {"type": "string", "required": False},
        },
    },
    {
        "name": "get_environment_context",
        "description": "Lista variaveis de ambiente e configuracoes necessarias para o contexto",
        "parameters": {
            "context": {"type": "string", "required": True},
            "repo_name": {"type": "string", "required": False},
        },
    },
    {
        "name": "analyze_change_impact",
        "description": "Analisa o impacto de uma mudanca planejada antes de implementar",
        "parameters": {
            "change_description": {"type": "string", "required": True, "description": "O que sera alterado"},
            "repo_name": {"type": "string", "required": True, "description": "Repositorio alvo"},
            "affected_files": {"type": "array", "required": False, "description": "Arquivos que serao modificados"},
        },
    },
]


# --- Auth helpers ---

def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _get_mcp_user(
    db: Session,
    authorization: str | None,
) -> tuple[str, str]:
    """Valida token MCP e retorna (org_id, user_id)."""
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Token MCP ausente")

    token = authorization[len("Bearer "):]
    token_hash = _hash_token(token)

    row = db.execute(text("""
        SELECT org_id, user_id FROM mcp_tokens
        WHERE token_hash = :hash AND is_active = true
    """), {"hash": token_hash}).mappings().first()

    if not row:
        raise HTTPException(status_code=401, detail="Token MCP invalido ou revogado")

    return row["org_id"], row["user_id"]


# --- Health ---

@router.get("/health")
def mcp_health():
    return {"status": "ok", "tools": len(MCP_TOOLS), "version": "1.0"}


# --- Tool listing ---

@router.get("/tools")
def list_tools(
    db: Session = Depends(get_session),
    authorization: str | None = Header(None),
):
    _get_mcp_user(db, authorization)
    return {"tools": MCP_TOOLS}


# --- Tool execution ---

class ToolCallRequest(BaseModel):
    name: str
    arguments: dict = {}


@router.post("/tools/call")
def call_tool(
    req: ToolCallRequest,
    db: Session = Depends(get_session),
    authorization: str | None = Header(None),
):
    org_id, user_id = _get_mcp_user(db, authorization)

    tool_fn = _TOOL_DISPATCH.get(req.name)
    if not tool_fn:
        raise HTTPException(status_code=404, detail=f"Tool '{req.name}' nao encontrada")

    try:
        result = tool_fn(db=db, org_id=org_id, **req.arguments)
        return {"result": result}
    except Exception as e:
        logger.error(f"MCP tool error ({req.name}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


def _call_search_code(db, org_id, **kwargs):
    return search_similar_code(db, org_id, kwargs["query"], kwargs.get("repo_name"), kwargs.get("top_k", 5))


def _call_rules(db, org_id, **kwargs):
    return get_business_rules(db, org_id, kwargs["context"], kwargs.get("rule_types"), kwargs.get("repo_name"))


def _call_patterns(db, org_id, **kwargs):
    return get_team_patterns(db, org_id, kwargs["context"], kwargs.get("language"), kwargs.get("repo_name"))


def _call_decisions(db, org_id, **kwargs):
    return get_architecture_decisions(db, org_id, kwargs["context"], kwargs.get("repo_name"))


def _call_env(db, org_id, **kwargs):
    return get_environment_context(db, org_id, kwargs["context"], kwargs.get("repo_name"))


def _call_impact(db, org_id, **kwargs):
    return analyze_change_impact(db, org_id, kwargs["change_description"], kwargs["repo_name"], kwargs.get("affected_files"))


_TOOL_DISPATCH = {
    "search_similar_code": _call_search_code,
    "get_business_rules": _call_rules,
    "get_team_patterns": _call_patterns,
    "get_architecture_decisions": _call_decisions,
    "get_environment_context": _call_env,
    "analyze_change_impact": _call_impact,
}


# --- Token management (dashboard endpoints) ---

token_router = APIRouter()


@token_router.post("/mcp/token")
def generate_mcp_token(
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """Gera um token MCP pessoal. O token so e exibido uma vez."""
    # Revoga tokens anteriores do usuario
    db.execute(text("""
        UPDATE mcp_tokens SET is_active = false, revoked_at = now()
        WHERE user_id = :user_id AND org_id = :org_id AND is_active = true
    """), {"user_id": user.id, "org_id": user.org_id})

    raw_token = f"mcp_{secrets.token_urlsafe(32)}"
    token_hash = _hash_token(raw_token)
    token_id = str(uuid.uuid4())

    db.execute(text("""
        INSERT INTO mcp_tokens (id, org_id, user_id, token_hash)
        VALUES (:id, :org_id, :user_id, :hash)
    """), {
        "id": token_id,
        "org_id": user.org_id,
        "user_id": user.id,
        "hash": token_hash,
    })
    db.commit()

    return {"token": raw_token, "id": token_id}


@token_router.delete("/mcp/token")
def revoke_mcp_token(
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """Revoga o token MCP ativo do usuario."""
    result = db.execute(text("""
        UPDATE mcp_tokens SET is_active = false, revoked_at = now()
        WHERE user_id = :user_id AND org_id = :org_id AND is_active = true
    """), {"user_id": user.id, "org_id": user.org_id})
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Nenhum token ativo encontrado")

    return {"revoked": True}


@token_router.get("/mcp/token/status")
def mcp_token_status(
    db: Session = Depends(get_session),
    user: User = Depends(require_role("admin", "dev")),
):
    """Verifica se o usuario tem um token MCP ativo."""
    row = db.execute(text("""
        SELECT id, created_at FROM mcp_tokens
        WHERE user_id = :user_id AND org_id = :org_id AND is_active = true
        LIMIT 1
    """), {"user_id": user.id, "org_id": user.org_id}).mappings().first()

    if not row:
        return {"has_token": False}

    return {
        "has_token": True,
        "token_id": row["id"],
        "created_at": str(row["created_at"]),
    }
