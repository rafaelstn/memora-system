"""Extrai regras de negocio do codigo indexado usando LLM."""

import json
import logging
import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.embedder import Embedder
from app.integrations import llm_router

logger = logging.getLogger(__name__)

EXTRACT_SYSTEM_PROMPT = (
    "Voce e um analista de negocios senior que analisa codigo para extrair regras de negocio. "
    "Responda sempre em portugues brasileiro. "
    "Extraia APENAS regras de negocio reais — ignore codigo de infraestrutura, "
    "configuracao, logging e tratamento generico de erros."
)

EXTRACT_USER_TEMPLATE = """Analise o codigo abaixo e extraia as regras de negocio presentes.
Para cada regra encontrada, responda em JSON (lista):
[{{
  "rule_type": "calculation|validation|permission|integration|conditional",
  "title": "titulo curto e descritivo",
  "description": "explicacao tecnica em portugues (2-3 frases)",
  "plain_english": "explicacao para nao-tecnico em 1 frase simples usando Se...Entao...Exceto",
  "conditions": [{{"if": "...", "then": "...", "except": "..."}}],
  "confidence": 0.0-1.0
}}]

Se nao houver regras de negocio: retorne [].

Arquivo: {file_path}
Funcao: {chunk_name}

Codigo:
{content}"""

# Nomes de arquivos que sugerem logica de negocio
BUSINESS_KEYWORDS = {
    "service", "calculator", "validator", "handler", "processor",
    "rules", "policy", "pricing", "discount", "commission", "tax",
    "billing", "payment", "order", "invoice", "shipping", "fee",
}

# Arquivos a ignorar
IGNORE_PATTERNS = {"config", "migration", "test", "conftest", "setup", "__init__"}


class RulesExtractor:
    def __init__(self, db: Session, org_id: str):
        self._db = db
        self._org_id = org_id
        self._embedder = Embedder()

    def extract(self, repo_name: str) -> list[dict]:
        """Extrai regras de negocio do repo indexado."""

        # 1. Identifica chunks com logica de negocio
        chunks = self._get_business_chunks(repo_name)
        if not chunks:
            logger.info(f"Nenhum chunk com logica de negocio em {repo_name}")
            return []

        # Reset changed_in_last_push flag
        self._db.execute(text("""
            UPDATE business_rules SET changed_in_last_push = false
            WHERE org_id = :org_id AND repo_name = :repo_name
        """), {"org_id": self._org_id, "repo_name": repo_name})

        all_rules = []

        # 2. Extrai regras de cada chunk via LLM
        for chunk in chunks:
            try:
                rules = self._extract_from_chunk(chunk)
                for rule in rules:
                    rule["file_path"] = chunk["file_path"]
                    rule["chunk_name"] = chunk["chunk_name"]
                all_rules.extend(rules)
            except Exception as e:
                logger.error(f"Erro ao extrair regras de {chunk['file_path']}: {e}")

        if not all_rules:
            self._db.commit()
            return []

        # 3. Deduplicacao e salvamento
        saved = self._deduplicate_and_save(repo_name, all_rules)

        self._db.commit()
        logger.info(f"Extraidas {len(saved)} regras de {repo_name}")
        return saved

    def _get_business_chunks(self, repo_name: str) -> list[dict]:
        """Busca chunks que provavelmente contem regras de negocio."""
        rows = self._db.execute(text("""
            SELECT file_path, chunk_name, chunk_type, content
            FROM code_chunks
            WHERE org_id = :org_id AND repo_name = :repo_name
            ORDER BY file_path, chunk_name
        """), {"org_id": self._org_id, "repo_name": repo_name}).mappings().all()

        business_chunks = []
        for r in rows:
            fp = r["file_path"].lower()
            filename = fp.split("/")[-1] if "/" in fp else fp

            # Skip ignored files
            if any(p in filename for p in IGNORE_PATTERNS):
                continue

            # Prioritize files with business keywords
            has_keyword = any(kw in fp for kw in BUSINESS_KEYWORDS)

            # Check for high density of conditionals
            content = r["content"]
            cond_count = content.count("if ") + content.count("elif ") + content.count("else:")
            has_logic = cond_count >= 2

            if has_keyword or has_logic:
                business_chunks.append(dict(r))

        return business_chunks[:30]  # Limita para nao estourar tokens

    def _extract_from_chunk(self, chunk: dict) -> list[dict]:
        """Extrai regras de um chunk via LLM."""
        user_message = EXTRACT_USER_TEMPLATE.format(
            file_path=chunk["file_path"],
            chunk_name=chunk["chunk_name"],
            content=chunk["content"][:4000],
        )

        result = llm_router.complete(
            db=self._db,
            system_prompt=EXTRACT_SYSTEM_PROMPT,
            user_message=user_message,
            org_id=self._org_id,
            max_tokens=2048,
        )

        content = result["content"].strip()

        # Parse JSON from response
        try:
            # Handle markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            rules = json.loads(content)
            if not isinstance(rules, list):
                rules = [rules] if isinstance(rules, dict) else []
            return rules
        except (json.JSONDecodeError, IndexError):
            logger.warning(f"Falha ao parsear JSON de regras: {content[:200]}")
            return []

    def _deduplicate_and_save(self, repo_name: str, rules: list[dict]) -> list[dict]:
        """Deduplica regras por similaridade e salva no banco."""
        saved = []

        for rule in rules:
            # Validate required fields
            if not all(k in rule for k in ("rule_type", "title", "description", "plain_english")):
                continue

            # Validate rule_type
            valid_types = {"calculation", "validation", "permission", "integration", "conditional"}
            if rule.get("rule_type") not in valid_types:
                continue

            # Generate embedding
            embed_text = f"{rule['title']} {rule['plain_english']}"
            try:
                embedding = self._embedder.embed_text(embed_text)
            except Exception:
                embedding = None

            # Check for duplicates
            is_duplicate = False
            if embedding:
                existing = self._db.execute(text("""
                    SELECT id, description FROM business_rules
                    WHERE org_id = :org_id AND repo_name = :repo_name
                      AND embedding <=> CAST(:embedding AS vector) < 0.08
                    LIMIT 1
                """), {
                    "org_id": self._org_id,
                    "repo_name": repo_name,
                    "embedding": str(embedding),
                }).mappings().first()

                if existing:
                    # Update existing rule
                    is_duplicate = True
                    self._db.execute(text("""
                        UPDATE business_rules
                        SET description = :description, plain_english = :plain_english,
                            conditions = :conditions, confidence = :confidence,
                            affected_files = :files, affected_functions = :functions,
                            embedding = CAST(:embedding AS vector),
                            last_verified_at = now(), updated_at = now()
                        WHERE id = :id
                    """), {
                        "description": rule["description"],
                        "plain_english": rule["plain_english"],
                        "conditions": json.dumps(rule.get("conditions", [])),
                        "confidence": min(1.0, max(0.0, float(rule.get("confidence", 0.5)))),
                        "files": json.dumps([rule.get("file_path", "")]),
                        "functions": json.dumps([rule.get("chunk_name", "")]),
                        "embedding": str(embedding),
                        "id": existing["id"],
                    })
                    saved.append({"id": existing["id"], "title": rule["title"], "action": "updated"})

            if not is_duplicate:
                rule_id = str(uuid.uuid4())
                self._db.execute(text("""
                    INSERT INTO business_rules
                        (id, org_id, repo_name, rule_type, title, description, plain_english,
                         conditions, affected_files, affected_functions, embedding, confidence)
                    VALUES (:id, :org_id, :repo_name, :rule_type, :title, :description, :plain_english,
                            :conditions, :files, :functions, CAST(:embedding AS vector), :confidence)
                """), {
                    "id": rule_id,
                    "org_id": self._org_id,
                    "repo_name": repo_name,
                    "rule_type": rule["rule_type"],
                    "title": rule["title"],
                    "description": rule["description"],
                    "plain_english": rule["plain_english"],
                    "conditions": json.dumps(rule.get("conditions", [])),
                    "files": json.dumps([rule.get("file_path", "")]),
                    "functions": json.dumps([rule.get("chunk_name", "")]),
                    "embedding": str(embedding) if embedding else None,
                    "confidence": min(1.0, max(0.0, float(rule.get("confidence", 0.5)))),
                })
                saved.append({"id": rule_id, "title": rule["title"], "action": "created"})

        return saved
