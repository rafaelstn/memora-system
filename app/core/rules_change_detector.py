"""Detecta mudancas em regras de negocio apos push no GitHub."""

import json
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations import llm_router

logger = logging.getLogger(__name__)

COMPARE_SYSTEM_PROMPT = (
    "Voce e um analista que compara versoes de regras de negocio. "
    "Responda em portugues brasileiro."
)

COMPARE_USER_TEMPLATE = """Compare a versao anterior e nova desta regra de negocio.

Regra anterior:
{previous}

Codigo novo:
{new_code}

A regra foi: (responda apenas com uma palavra)
- "mantida" se a logica e a mesma
- "modificada" se a logica mudou
- "removida" se a regra nao existe mais no codigo novo"""


class RulesChangeDetector:
    def __init__(self, db: Session, org_id: str):
        self._db = db
        self._org_id = org_id

    def detect_changes(self, repo_name: str, changed_files: list[str]) -> list[dict]:
        """Detecta mudancas em regras apos alteracao de arquivos."""
        if not changed_files:
            return []

        # Busca regras que referenciam os arquivos alterados
        alerts = []

        for file_path in changed_files:
            affected_rules = self._db.execute(text("""
                SELECT id, title, description, plain_english, affected_files
                FROM business_rules
                WHERE org_id = :org_id AND repo_name = :repo_name
                  AND is_active = true
                  AND affected_files::text LIKE :file_pattern
            """), {
                "org_id": self._org_id,
                "repo_name": repo_name,
                "file_pattern": f"%{file_path}%",
            }).mappings().all()

            if not affected_rules:
                continue

            # Busca codigo novo do arquivo
            new_chunks = self._db.execute(text("""
                SELECT content FROM code_chunks
                WHERE org_id = :org_id AND repo_name = :repo_name
                  AND file_path = :file_path
                LIMIT 5
            """), {
                "org_id": self._org_id,
                "repo_name": repo_name,
                "file_path": file_path,
            }).mappings().all()

            new_code = "\n".join([c["content"][:2000] for c in new_chunks]) if new_chunks else ""

            for rule in affected_rules:
                change = self._check_rule_change(rule, new_code)
                if change:
                    alert = self._create_alert(rule, change, new_code)
                    if alert:
                        alerts.append(alert)

        self._db.commit()
        return alerts

    def _check_rule_change(self, rule: dict, new_code: str) -> str | None:
        """Verifica se uma regra mudou usando LLM."""
        if not new_code:
            return "removed"

        try:
            result = llm_router.complete(
                db=self._db,
                system_prompt=COMPARE_SYSTEM_PROMPT,
                user_message=COMPARE_USER_TEMPLATE.format(
                    previous=rule["description"],
                    new_code=new_code[:4000],
                ),
                org_id=self._org_id,
                max_tokens=50,
            )
            answer = result["content"].strip().lower()

            if "modificada" in answer:
                return "modified"
            elif "removida" in answer:
                return "removed"
            return None  # mantida
        except Exception as e:
            logger.error(f"Erro ao comparar regra {rule['id']}: {e}")
            return None

    def _create_alert(self, rule: dict, change_type: str, new_code: str) -> dict | None:
        """Cria alerta de mudanca de regra."""
        alert_id = str(uuid.uuid4())

        # Gera nova descricao se modificada
        new_description = None
        if change_type == "modified" and new_code:
            try:
                result = llm_router.complete(
                    db=self._db,
                    system_prompt="Descreva a regra de negocio presente neste codigo em portugues, em 2-3 frases.",
                    user_message=new_code[:4000],
                    org_id=self._org_id,
                    max_tokens=300,
                )
                new_description = result["content"].strip()
            except Exception:
                new_description = "(Nao foi possivel gerar nova descricao)"

        self._db.execute(text("""
            INSERT INTO rule_change_alerts
                (id, org_id, rule_id, change_type, previous_description, new_description)
            VALUES (:id, :org_id, :rule_id, :change_type, :previous, :new_desc)
        """), {
            "id": alert_id,
            "org_id": self._org_id,
            "rule_id": rule["id"],
            "change_type": change_type,
            "previous": rule["description"],
            "new_desc": new_description,
        })

        # Mark rule as changed
        if change_type == "modified":
            self._db.execute(text("""
                UPDATE business_rules
                SET changed_in_last_push = true, description = COALESCE(:new_desc, description),
                    updated_at = now()
                WHERE id = :id
            """), {"new_desc": new_description, "id": rule["id"]})
        elif change_type == "removed":
            self._db.execute(text("""
                UPDATE business_rules SET is_active = false, changed_in_last_push = true, updated_at = now()
                WHERE id = :id
            """), {"id": rule["id"]})

        return {
            "alert_id": alert_id,
            "rule_id": rule["id"],
            "rule_title": rule["title"],
            "change_type": change_type,
        }
