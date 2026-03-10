"""Endpoints para Regras de Negocio Invisiveis."""

import json
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.api.deps import get_current_product, get_current_user, get_data_session, require_role
from app.core.embedder import Embedder
from app.db.session import SessionLocal
from app.models.product import Product
from app.models.user import User

# Restricted router (admin + dev)
router = APIRouter(dependencies=[Depends(require_role("admin", "dev"))])

# Public router (any authenticated user)
public_router = APIRouter(dependencies=[Depends(require_role("admin", "dev", "suporte"))])

logger = logging.getLogger(__name__)


# ---------- Request models ----------

class SimulateRequest(BaseModel):
    input_values: dict


# ---------- Background tasks ----------

def _extract_rules_bg(repo_name: str, org_id: str):
    db = SessionLocal()
    try:
        from app.core.rules_extractor import RulesExtractor
        extractor = RulesExtractor(db, org_id)
        result = extractor.extract(repo_name)
        logger.info(f"Regras extraidas para {repo_name}: {len(result)} regras")
    except Exception as e:
        logger.error(f"Extracao de regras falhou para {repo_name}: {e}")
    finally:
        db.close()


# ---------- Extraction endpoints ----------

@router.post("/rules/extract/{repo_name}", status_code=202)
def extract_rules(
    repo_name: str,
    background_tasks: BackgroundTasks,
    user: User = Depends(get_current_user),
    product: Product = Depends(get_current_product),
):
    """Dispara extracao completa de regras em background."""
    background_tasks.add_task(_extract_rules_bg, repo_name, user.org_id)
    return {"status": "extracting", "repo_name": repo_name}


@router.get("/rules/extract/status/{repo_name}")
def extract_status(
    repo_name: str,
    db: Session = Depends(get_data_session),
    user: User = Depends(get_current_user),
    product: Product = Depends(get_current_product),
):
    """Status da extracao — conta regras existentes."""
    row = db.execute(text("""
        SELECT COUNT(*) as total,
               MAX(extracted_at) as last_extracted,
               SUM(CASE WHEN changed_in_last_push THEN 1 ELSE 0 END) as changed
        FROM business_rules
        WHERE product_id = :product_id AND repo_name = :repo_name AND is_active = true
    """), {"product_id": product.id, "repo_name": repo_name}).mappings().first()

    return {
        "total_rules": row["total"] if row else 0,
        "last_extracted": str(row["last_extracted"]) if row and row["last_extracted"] else None,
        "changed_since_push": row["changed"] if row else 0,
    }


# ---------- Rules CRUD ----------

@public_router.get("/rules")
def list_rules(
    repo_name: str = Query(None),
    rule_type: str = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_data_session),
    user: User = Depends(get_current_user),
    product: Product = Depends(get_current_product),
):
    """Lista regras com filtros."""
    from app.core.query_builder import build_where_clause

    conditions = ["product_id = :product_id", "is_active = true"]
    params: dict = {"product_id": product.id}

    if repo_name:
        conditions.append("repo_name = :repo_name")
        params["repo_name"] = repo_name
    if rule_type:
        conditions.append("rule_type = :rule_type")
        params["rule_type"] = rule_type

    where = build_where_clause("business_rules", conditions)
    offset = (page - 1) * per_page
    params["limit"] = per_page
    params["offset"] = offset

    rows = db.execute(text(f"""
        SELECT id, repo_name, rule_type, title, plain_english, confidence,
               changed_in_last_push, affected_files, extracted_at
        FROM business_rules
        WHERE {where}
        ORDER BY rule_type, title
        LIMIT :limit OFFSET :offset
    """), params).mappings().all()

    count = db.execute(text(f"""
        SELECT COUNT(*) as total FROM business_rules WHERE {where}
    """), {k: v for k, v in params.items() if k not in ("limit", "offset")}).mappings().first()

    return {
        "rules": [
            {
                "id": r["id"],
                "repo_name": r["repo_name"],
                "rule_type": r["rule_type"],
                "title": r["title"],
                "plain_english": r["plain_english"],
                "confidence": r["confidence"],
                "changed_in_last_push": r["changed_in_last_push"],
                "affected_files": r["affected_files"],
                "extracted_at": str(r["extracted_at"]) if r["extracted_at"] else None,
            }
            for r in rows
        ],
        "total": count["total"] if count else 0,
        "page": page,
        "per_page": per_page,
    }


@public_router.get("/rules/search")
def search_rules(
    q: str = Query(..., min_length=2),
    repo_name: str = Query(None),
    db: Session = Depends(get_data_session),
    user: User = Depends(get_current_user),
    product: Product = Depends(get_current_product),
):
    """Busca semantica nas regras."""
    embedder = Embedder()
    embedding = embedder.embed_text(q)

    repo_filter = "AND repo_name = :repo_name" if repo_name else ""
    params: dict = {
        "product_id": product.id,
        "embedding": str(embedding),
        "top_k": 10,
    }
    if repo_name:
        params["repo_name"] = repo_name

    rows = db.execute(text(f"""
        SELECT id, repo_name, rule_type, title, plain_english, description,
               confidence, affected_files,
               embedding <=> CAST(:embedding AS vector) AS distance
        FROM business_rules
        WHERE product_id = :product_id AND is_active = true AND embedding IS NOT NULL
          {repo_filter}
        ORDER BY embedding <=> CAST(:embedding AS vector)
        LIMIT :top_k
    """), params).mappings().all()

    return [
        {
            "id": r["id"],
            "repo_name": r["repo_name"],
            "rule_type": r["rule_type"],
            "title": r["title"],
            "plain_english": r["plain_english"],
            "description": r["description"],
            "confidence": r["confidence"],
            "affected_files": r["affected_files"],
            "score": round(1 - r["distance"], 4) if r["distance"] else 0,
        }
        for r in rows
    ]


@public_router.get("/rules/{rule_id}")
def get_rule(
    rule_id: str,
    db: Session = Depends(get_data_session),
    user: User = Depends(get_current_user),
    product: Product = Depends(get_current_product),
):
    """Detalhe completo de uma regra."""
    row = db.execute(text("""
        SELECT id, repo_name, rule_type, title, description, plain_english,
               conditions, affected_files, affected_functions, confidence,
               is_active, changed_in_last_push, last_verified_at,
               extracted_at, created_at, updated_at
        FROM business_rules
        WHERE id = :id AND product_id = :product_id
    """), {"id": rule_id, "product_id": product.id}).mappings().first()

    if not row:
        raise HTTPException(status_code=404, detail="Regra nao encontrada")

    # Busca ultimas mudancas
    changes = db.execute(text("""
        SELECT change_type, previous_description, new_description, detected_at
        FROM rule_change_alerts
        WHERE rule_id = :rule_id AND org_id = :org_id
        ORDER BY detected_at DESC
        LIMIT 3
    """), {"rule_id": rule_id, "org_id": user.org_id}).mappings().all()

    # Busca ultimas simulacoes do usuario
    simulations = db.execute(text("""
        SELECT id, input_values, result, created_at
        FROM rule_simulations
        WHERE rule_id = :rule_id AND simulated_by = :user_id
        ORDER BY created_at DESC
        LIMIT 5
    """), {"rule_id": rule_id, "user_id": user.id}).mappings().all()

    return {
        "id": row["id"],
        "repo_name": row["repo_name"],
        "rule_type": row["rule_type"],
        "title": row["title"],
        "description": row["description"],
        "plain_english": row["plain_english"],
        "conditions": row["conditions"],
        "affected_files": row["affected_files"],
        "affected_functions": row["affected_functions"],
        "confidence": row["confidence"],
        "is_active": row["is_active"],
        "changed_in_last_push": row["changed_in_last_push"],
        "last_verified_at": str(row["last_verified_at"]) if row["last_verified_at"] else None,
        "extracted_at": str(row["extracted_at"]) if row["extracted_at"] else None,
        "created_at": str(row["created_at"]) if row["created_at"] else None,
        "updated_at": str(row["updated_at"]) if row["updated_at"] else None,
        "changes": [
            {
                "change_type": c["change_type"],
                "previous_description": c["previous_description"],
                "new_description": c["new_description"],
                "detected_at": str(c["detected_at"]) if c["detected_at"] else None,
            }
            for c in changes
        ],
        "simulations": [
            {
                "id": s["id"],
                "input_values": s["input_values"],
                "result": s["result"],
                "created_at": str(s["created_at"]) if s["created_at"] else None,
            }
            for s in simulations
        ],
    }


# ---------- Simulation ----------

@public_router.post("/rules/{rule_id}/simulate")
def simulate_rule(
    rule_id: str,
    body: SimulateRequest,
    db: Session = Depends(get_data_session),
    user: User = Depends(get_current_user),
    product: Product = Depends(get_current_product),
):
    """Simula uma regra com valores de entrada."""
    from app.core.rules_simulator import RulesSimulator
    simulator = RulesSimulator(db, user.org_id)
    result = simulator.simulate(rule_id, body.input_values, user.id)

    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])

    return result


# ---------- Alerts ----------

@router.get("/rules/alerts")
def list_alerts(
    repo_name: str = Query(None),
    acknowledged: bool = Query(False),
    db: Session = Depends(get_data_session),
    user: User = Depends(get_current_user),
    product: Product = Depends(get_current_product),
):
    """Lista alertas de mudanca de regras."""
    conditions = ["r.product_id = :product_id"]
    params: dict = {"product_id": product.id}

    if not acknowledged:
        conditions.append("a.acknowledged_by IS NULL")

    if repo_name:
        conditions.append("r.repo_name = :repo_name")
        params["repo_name"] = repo_name

    where = " AND ".join(conditions)

    rows = db.execute(text(f"""
        SELECT a.id, a.rule_id, a.change_type, a.previous_description,
               a.new_description, a.detected_at, a.acknowledged_by, a.acknowledged_at,
               r.title as rule_title, r.repo_name
        FROM rule_change_alerts a
        JOIN business_rules r ON r.id = a.rule_id
        WHERE {where}
        ORDER BY a.detected_at DESC
        LIMIT 50
    """), params).mappings().all()

    return [
        {
            "id": r["id"],
            "rule_id": r["rule_id"],
            "rule_title": r["rule_title"],
            "repo_name": r["repo_name"],
            "change_type": r["change_type"],
            "previous_description": r["previous_description"],
            "new_description": r["new_description"],
            "detected_at": str(r["detected_at"]) if r["detected_at"] else None,
            "acknowledged": r["acknowledged_by"] is not None,
        }
        for r in rows
    ]


@router.patch("/rules/alerts/{alert_id}/acknowledge")
def acknowledge_alert(
    alert_id: str,
    db: Session = Depends(get_data_session),
    user: User = Depends(get_current_user),
    product: Product = Depends(get_current_product),
):
    """Marca alerta como reconhecido."""
    result = db.execute(text("""
        UPDATE rule_change_alerts
        SET acknowledged_by = :user_id, acknowledged_at = now()
        WHERE id = :id AND org_id = :org_id AND acknowledged_by IS NULL
    """), {"user_id": user.id, "id": alert_id, "org_id": user.org_id})
    db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="Alerta nao encontrado ou ja reconhecido")

    return {"acknowledged": True}
