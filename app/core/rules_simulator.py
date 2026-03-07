"""Simula regras de negocio com valores de entrada fornecidos pelo usuario."""

import json
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.integrations import llm_router

logger = logging.getLogger(__name__)

SIMULATE_SYSTEM_PROMPT = (
    "Voce e um analista de negocios que simula regras implementadas em codigo. "
    "Explique passo a passo o que acontece e qual e o resultado final. "
    "Responda em portugues simples, como se estivesse explicando para alguem de negocio. "
    "Seja especifico com os valores calculados."
)

SIMULATE_USER_TEMPLATE = """Dada a seguinte regra de negocio implementada no codigo:

Titulo: {title}
Descricao: {description}
Linguagem simples: {plain_english}

Condicoes: {conditions}

Codigo de implementacao:
{code}

Simule o resultado para os seguintes valores de entrada:
{input_values}

Explique passo a passo o que acontece e qual e o resultado final."""


class RulesSimulator:
    def __init__(self, db: Session, org_id: str):
        self._db = db
        self._org_id = org_id

    def simulate(self, rule_id: str, input_values: dict, user_id: str) -> dict:
        """Simula uma regra com valores de entrada."""

        # Busca a regra
        rule = self._db.execute(text("""
            SELECT id, title, description, plain_english, conditions,
                   affected_files, affected_functions, repo_name
            FROM business_rules
            WHERE id = :id AND org_id = :org_id
        """), {"id": rule_id, "org_id": self._org_id}).mappings().first()

        if not rule:
            return {"error": "Regra nao encontrada"}

        # Busca codigo fonte
        code = self._get_rule_code(rule)

        # Formata valores de entrada
        input_str = "\n".join([f"- {k}: {v}" for k, v in input_values.items()])

        conditions_str = json.dumps(rule["conditions"], ensure_ascii=False) if rule["conditions"] else "N/A"

        user_message = SIMULATE_USER_TEMPLATE.format(
            title=rule["title"],
            description=rule["description"],
            plain_english=rule["plain_english"],
            conditions=conditions_str,
            code=code[:6000],
            input_values=input_str,
        )

        try:
            result = llm_router.complete(
                db=self._db,
                system_prompt=SIMULATE_SYSTEM_PROMPT,
                user_message=user_message,
                org_id=self._org_id,
                max_tokens=1024,
            )
            simulation_result = result["content"]
        except Exception as e:
            logger.error(f"Simulacao falhou para regra {rule_id}: {e}")
            return {"error": str(e)}

        # Salva simulacao
        sim_id = str(uuid.uuid4())
        self._db.execute(text("""
            INSERT INTO rule_simulations (id, org_id, rule_id, simulated_by, input_values, result)
            VALUES (:id, :org_id, :rule_id, :user_id, :input_values, :result)
        """), {
            "id": sim_id,
            "org_id": self._org_id,
            "rule_id": rule_id,
            "user_id": user_id,
            "input_values": json.dumps(input_values, ensure_ascii=False),
            "result": simulation_result,
        })
        self._db.commit()

        return {
            "simulation_id": sim_id,
            "rule_id": rule_id,
            "rule_title": rule["title"],
            "input_values": input_values,
            "result": simulation_result,
        }

    def _get_rule_code(self, rule: dict) -> str:
        """Busca codigo fonte das funcoes afetadas pela regra."""
        files = rule["affected_files"] or []
        functions = rule["affected_functions"] or []

        if not files:
            return "(Codigo fonte nao disponivel)"

        parts = []
        for fp in files[:3]:
            rows = self._db.execute(text("""
                SELECT chunk_name, chunk_type, content
                FROM code_chunks
                WHERE org_id = :org_id AND repo_name = :repo_name AND file_path = :fp
                ORDER BY chunk_name
                LIMIT 5
            """), {
                "org_id": self._org_id,
                "repo_name": rule["repo_name"],
                "fp": fp,
            }).mappings().all()

            for r in rows:
                # Prioriza funcoes especificas se conhecidas
                if functions and r["chunk_name"] not in functions:
                    continue
                parts.append(f"# {fp} — {r['chunk_name']}\n{r['content'][:2000]}")

            # Se nao encontrou funcoes especificas, pega todas
            if not parts:
                for r in rows:
                    parts.append(f"# {fp} — {r['chunk_name']}\n{r['content'][:2000]}")

        return "\n\n".join(parts) if parts else "(Codigo fonte nao disponivel)"
