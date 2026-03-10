"""Gerenciamento de banco de dados Enterprise.

Responsavel por:
- Testar conexao com banco externo do cliente
- Executar migrations no banco do cliente
- Fornecer engine/session para o banco do cliente (por request)
- Health check periodico do banco do cliente
"""
import logging
import time
import uuid
from collections.abc import Generator
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.encryption import decrypt_api_key, encrypt_api_key
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)


def _build_dsn(host: str, port: int, database: str, username: str, password: str, ssl_mode: str = "require") -> str:
    """Constroi DSN PostgreSQL a partir dos componentes."""
    return f"postgresql://{username}:{password}@{host}:{port}/{database}?sslmode={ssl_mode}"


def test_connection(host: str, port: int, database: str, username: str, password: str, ssl_mode: str = "require") -> dict:
    """Testa conexao com o banco externo sem salvar nada.

    Returns:
        {"success": True/False, "message": str, "version": str | None}
    """
    dsn = _build_dsn(host, port, database, username, password, ssl_mode)
    try:
        eng = create_engine(dsn, pool_pre_ping=True, pool_size=1, max_overflow=0)
        with eng.connect() as conn:
            version = conn.execute(text("SELECT version()")).scalar()
            # Verificar se pgvector esta instalado
            has_vector = conn.execute(text(
                "SELECT 1 FROM pg_extension WHERE extname = 'vector'"
            )).first()
        eng.dispose()
        if not has_vector:
            return {
                "success": False,
                "message": "Extensao pgvector nao encontrada. Instale com: CREATE EXTENSION vector;",
                "version": version,
            }
        return {"success": True, "message": "Conexao bem-sucedida", "version": version}
    except Exception as e:
        return {"success": False, "message": str(e), "version": None}


def save_config(org_id: str, host: str, port: int, database: str, username: str, password: str, ssl_mode: str = "require") -> str:
    """Salva credenciais criptografadas no Supabase. Retorna o config_id."""
    db = SessionLocal()
    try:
        config_id = str(uuid.uuid4())
        db.execute(text("""
            INSERT INTO enterprise_db_configs (id, org_id, host_encrypted, port, database_name_encrypted, username_encrypted, password_encrypted, ssl_mode)
            VALUES (:id, :org_id, :host, :port, :database, :username, :password, :ssl_mode)
            ON CONFLICT (org_id) DO UPDATE SET
                host_encrypted = EXCLUDED.host_encrypted,
                port = EXCLUDED.port,
                database_name_encrypted = EXCLUDED.database_name_encrypted,
                username_encrypted = EXCLUDED.username_encrypted,
                password_encrypted = EXCLUDED.password_encrypted,
                ssl_mode = EXCLUDED.ssl_mode,
                setup_complete = false,
                updated_at = now()
        """), {
            "id": config_id,
            "org_id": org_id,
            "host": encrypt_api_key(host),
            "port": port,
            "database": encrypt_api_key(database),
            "username": encrypt_api_key(username),
            "password": encrypt_api_key(password),
            "ssl_mode": ssl_mode,
        })
        db.commit()
        return config_id
    finally:
        db.close()


def _get_decrypted_config(org_id: str) -> dict | None:
    """Busca e descriptografa as credenciais do banco Enterprise."""
    db = SessionLocal()
    try:
        row = db.execute(text(
            "SELECT * FROM enterprise_db_configs WHERE org_id = :org_id"
        ), {"org_id": org_id}).mappings().first()
        if not row:
            return None
        return {
            "host": decrypt_api_key(row["host_encrypted"]),
            "port": row["port"],
            "database": decrypt_api_key(row["database_name_encrypted"]),
            "username": decrypt_api_key(row["username_encrypted"]),
            "password": decrypt_api_key(row["password_encrypted"]),
            "ssl_mode": row["ssl_mode"],
            "setup_complete": row["setup_complete"],
        }
    finally:
        db.close()


# Cache de engines Enterprise (org_id -> Engine). Evita criar engine por request.
_engine_cache: dict[str, Engine] = {}


def get_engine(org_id: str) -> Engine:
    """Retorna engine SQLAlchemy para o banco do cliente Enterprise.

    Usa cache em memoria — o mesmo engine (com pool) e reutilizado entre requests.
    Para invalidar (ex: apos update de credenciais), chamar invalidate_engine_cache(org_id).
    """
    if org_id in _engine_cache:
        return _engine_cache[org_id]

    config = _get_decrypted_config(org_id)
    if not config:
        raise ValueError(f"Configuracao Enterprise nao encontrada para org {org_id}")
    if not config["setup_complete"]:
        raise ValueError("Setup Enterprise ainda nao foi concluido")

    dsn = _build_dsn(config["host"], config["port"], config["database"], config["username"], config["password"], config["ssl_mode"])
    eng = create_engine(dsn, pool_pre_ping=True, pool_size=5, max_overflow=10)
    _engine_cache[org_id] = eng
    logger.info(f"Engine Enterprise criado e cacheado para org {org_id}")
    return eng


def invalidate_engine_cache(org_id: str):
    """Remove engine do cache e fecha conexoes. Chamar apos update de credenciais."""
    eng = _engine_cache.pop(org_id, None)
    if eng:
        eng.dispose()
        logger.info(f"Engine Enterprise invalidado para org {org_id}")


def get_enterprise_session(org_id: str) -> Session:
    """Retorna uma sessao para o banco Enterprise do cliente."""
    eng = get_engine(org_id)
    factory = sessionmaker(bind=eng)
    return factory()


# ---------------------------------------------------------------------------
# Migrations para o banco do cliente
# ---------------------------------------------------------------------------

# Tabelas operacionais — tudo que roda no banco do cliente Enterprise.
# Nota: organizations, users, invites, llm_providers, github_integration,
# notification_preferences, alert_webhooks, enterprise_db_configs ficam no Supabase.

_OPERATIONAL_TABLES_SQL = [
    # pgvector extension
    ("pgvector extension", "CREATE EXTENSION IF NOT EXISTS vector"),

    # products + memberships
    ("products", """
        CREATE TABLE IF NOT EXISTS products (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            name VARCHAR(255) NOT NULL,
            description TEXT,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_products_org ON products(org_id);
    """),
    ("product_memberships", """
        CREATE TABLE IF NOT EXISTS product_memberships (
            id VARCHAR(36) PRIMARY KEY,
            product_id VARCHAR(36) NOT NULL REFERENCES products(id),
            user_id VARCHAR(36) NOT NULL,
            created_at TIMESTAMP DEFAULT now(),
            CONSTRAINT uq_product_user UNIQUE (product_id, user_id)
        );
        CREATE INDEX IF NOT EXISTS idx_pm_product ON product_memberships(product_id);
        CREATE INDEX IF NOT EXISTS idx_pm_user ON product_memberships(user_id);
    """),

    # code_chunks (Module 1)
    ("code_chunks", """
        CREATE TABLE IF NOT EXISTS code_chunks (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            product_id VARCHAR(36) REFERENCES products(id),
            repo_name VARCHAR(255) NOT NULL,
            file_path TEXT NOT NULL,
            chunk_name VARCHAR(500) NOT NULL,
            chunk_type VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            embedding vector(1536),
            token_count INTEGER,
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_code_chunks_repo ON code_chunks(repo_name);
        CREATE INDEX IF NOT EXISTS idx_code_chunks_org ON code_chunks(org_id);
        CREATE INDEX IF NOT EXISTS idx_code_chunks_product ON code_chunks(product_id);
        CREATE INDEX IF NOT EXISTS idx_code_chunks_embedding
            ON code_chunks USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
    """),

    # conversations + messages (Module 1)
    ("conversations", """
        CREATE TABLE IF NOT EXISTS conversations (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            product_id VARCHAR(36) REFERENCES products(id),
            repo_name VARCHAR(255) NOT NULL,
            user_id VARCHAR(36) NOT NULL,
            title VARCHAR(500) NOT NULL,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_conversations_repo ON conversations(repo_name);
        CREATE INDEX IF NOT EXISTS idx_conversations_user ON conversations(user_id);
        CREATE INDEX IF NOT EXISTS idx_conversations_org ON conversations(org_id);
        CREATE INDEX IF NOT EXISTS idx_conversations_product ON conversations(product_id);
    """),
    ("messages", """
        CREATE TABLE IF NOT EXISTS messages (
            id VARCHAR(36) PRIMARY KEY,
            conversation_id VARCHAR(36) NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            role VARCHAR(20) NOT NULL,
            content TEXT NOT NULL,
            sources JSONB,
            model_used VARCHAR(100),
            tokens_used INTEGER,
            cost_usd NUMERIC(12, 8),
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
    """),

    # Monitor (Module 2)
    ("monitored_projects", """
        CREATE TABLE IF NOT EXISTS monitored_projects (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            product_id VARCHAR(36) REFERENCES products(id),
            name VARCHAR(255) NOT NULL,
            description VARCHAR(500),
            token VARCHAR(255) UNIQUE NOT NULL,
            token_preview VARCHAR(8) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_by VARCHAR(36) NOT NULL,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_monitored_projects_org ON monitored_projects(org_id);
        CREATE INDEX IF NOT EXISTS idx_monitored_projects_product ON monitored_projects(product_id);
        CREATE INDEX IF NOT EXISTS idx_monitored_projects_token ON monitored_projects(token);
    """),
    ("log_entries", """
        CREATE TABLE IF NOT EXISTS log_entries (
            id VARCHAR(36) PRIMARY KEY,
            project_id VARCHAR(36) NOT NULL REFERENCES monitored_projects(id),
            org_id VARCHAR(36) NOT NULL,
            level VARCHAR(20) NOT NULL,
            message TEXT NOT NULL,
            source VARCHAR(500),
            stack_trace TEXT,
            metadata JSONB,
            received_at TIMESTAMP DEFAULT now(),
            occurred_at TIMESTAMP,
            is_analyzed BOOLEAN NOT NULL DEFAULT false,
            raw_payload JSONB
        );
        CREATE INDEX IF NOT EXISTS idx_log_entries_project ON log_entries(project_id);
        CREATE INDEX IF NOT EXISTS idx_log_entries_org ON log_entries(org_id);
        CREATE INDEX IF NOT EXISTS idx_log_entries_level ON log_entries(level);
        CREATE INDEX IF NOT EXISTS idx_log_entries_received ON log_entries(received_at DESC);
    """),
    ("error_alerts", """
        CREATE TABLE IF NOT EXISTS error_alerts (
            id VARCHAR(36) PRIMARY KEY,
            project_id VARCHAR(36) NOT NULL REFERENCES monitored_projects(id),
            org_id VARCHAR(36) NOT NULL,
            log_entry_id VARCHAR(36) NOT NULL REFERENCES log_entries(id),
            title VARCHAR(500) NOT NULL,
            explanation TEXT NOT NULL,
            severity VARCHAR(20) NOT NULL,
            affected_component VARCHAR(255),
            suggested_actions JSONB,
            status VARCHAR(20) NOT NULL DEFAULT 'open',
            acknowledged_by VARCHAR(36),
            acknowledged_at TIMESTAMP,
            resolved_by VARCHAR(36),
            resolved_at TIMESTAMP,
            notification_sent BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_error_alerts_project ON error_alerts(project_id);
        CREATE INDEX IF NOT EXISTS idx_error_alerts_org ON error_alerts(org_id);
        CREATE INDEX IF NOT EXISTS idx_error_alerts_status ON error_alerts(status);
        CREATE INDEX IF NOT EXISTS idx_error_alerts_severity ON error_alerts(severity);
    """),

    # Knowledge (Module 3)
    ("knowledge_entries", """
        CREATE TABLE IF NOT EXISTS knowledge_entries (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            product_id VARCHAR(36) REFERENCES products(id),
            repo_id VARCHAR(36),
            source_type VARCHAR(20) NOT NULL,
            source_id VARCHAR(255),
            source_url VARCHAR(1024),
            title VARCHAR(500) NOT NULL,
            content TEXT NOT NULL,
            summary TEXT,
            embedding vector(1536),
            file_paths JSONB,
            components JSONB,
            decision_type VARCHAR(50),
            extracted_at TIMESTAMP DEFAULT now(),
            source_date TIMESTAMP,
            created_by VARCHAR(36),
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_entries_org ON knowledge_entries(org_id);
        CREATE INDEX IF NOT EXISTS idx_knowledge_entries_product ON knowledge_entries(product_id);
        CREATE INDEX IF NOT EXISTS idx_knowledge_entries_repo ON knowledge_entries(repo_id);
        CREATE INDEX IF NOT EXISTS idx_knowledge_entries_source_type ON knowledge_entries(source_type);
        CREATE INDEX IF NOT EXISTS idx_knowledge_entries_decision_type ON knowledge_entries(decision_type);
        CREATE INDEX IF NOT EXISTS idx_knowledge_entries_source_date ON knowledge_entries(source_date DESC);
        CREATE INDEX IF NOT EXISTS idx_knowledge_entries_embedding
            ON knowledge_entries USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
    """),
    ("knowledge_documents", """
        CREATE TABLE IF NOT EXISTS knowledge_documents (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            repo_id VARCHAR(36),
            filename VARCHAR(500) NOT NULL,
            file_type VARCHAR(20) NOT NULL,
            file_size INTEGER NOT NULL,
            storage_path VARCHAR(1024) NOT NULL,
            processed BOOLEAN NOT NULL DEFAULT false,
            entry_id VARCHAR(36) REFERENCES knowledge_entries(id),
            uploaded_by VARCHAR(36) NOT NULL,
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_documents_org ON knowledge_documents(org_id);
    """),
    ("knowledge_wikis", """
        CREATE TABLE IF NOT EXISTS knowledge_wikis (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            repo_id VARCHAR(36),
            component_name VARCHAR(255) NOT NULL,
            component_path VARCHAR(1024) NOT NULL,
            content TEXT NOT NULL,
            last_generated_at TIMESTAMP DEFAULT now(),
            generation_version INTEGER NOT NULL DEFAULT 1,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_knowledge_wikis_org ON knowledge_wikis(org_id);
        CREATE INDEX IF NOT EXISTS idx_knowledge_wikis_repo ON knowledge_wikis(repo_id);
        CREATE INDEX IF NOT EXISTS idx_knowledge_wikis_component ON knowledge_wikis(component_path);
    """),

    # Code Reviews (Module 4)
    ("code_reviews", """
        CREATE TABLE IF NOT EXISTS code_reviews (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            product_id VARCHAR(36) REFERENCES products(id),
            repo_name VARCHAR(255) NOT NULL,
            pr_number INTEGER,
            pr_title VARCHAR(500),
            pr_url VARCHAR(1024),
            pr_author VARCHAR(255),
            review_type VARCHAR(20) NOT NULL DEFAULT 'manual',
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            code_content TEXT,
            language VARCHAR(50),
            overall_score INTEGER,
            overall_verdict VARCHAR(30),
            summary TEXT,
            created_by VARCHAR(36),
            created_at TIMESTAMP DEFAULT now(),
            completed_at TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_code_reviews_org ON code_reviews(org_id);
        CREATE INDEX IF NOT EXISTS idx_code_reviews_product ON code_reviews(product_id);
        CREATE INDEX IF NOT EXISTS idx_code_reviews_repo ON code_reviews(repo_name);
    """),
    ("review_findings", """
        CREATE TABLE IF NOT EXISTS review_findings (
            id VARCHAR(36) PRIMARY KEY,
            review_id VARCHAR(36) NOT NULL REFERENCES code_reviews(id) ON DELETE CASCADE,
            org_id VARCHAR(36) NOT NULL,
            category VARCHAR(50) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            title VARCHAR(500) NOT NULL,
            description TEXT NOT NULL,
            suggestion TEXT,
            file_path VARCHAR(1024),
            line_start INTEGER,
            line_end INTEGER,
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_review_findings_review ON review_findings(review_id);
    """),

    # Incidents
    ("incidents", """
        CREATE TABLE IF NOT EXISTS incidents (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            project_id VARCHAR(36) REFERENCES monitored_projects(id),
            alert_id VARCHAR(36) REFERENCES error_alerts(id),
            title VARCHAR(500) NOT NULL,
            description TEXT,
            severity VARCHAR(20) NOT NULL DEFAULT 'medium',
            status VARCHAR(20) NOT NULL DEFAULT 'investigating',
            declared_by VARCHAR(36) NOT NULL,
            mitigated_at TIMESTAMP,
            resolved_at TIMESTAMP,
            resolution_summary TEXT,
            share_token VARCHAR(255) UNIQUE,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_incidents_org ON incidents(org_id);
        CREATE INDEX IF NOT EXISTS idx_incidents_status ON incidents(status);
        CREATE INDEX IF NOT EXISTS idx_incidents_project ON incidents(project_id);
    """),
    ("incident_timeline", """
        CREATE TABLE IF NOT EXISTS incident_timeline (
            id VARCHAR(36) PRIMARY KEY,
            incident_id VARCHAR(36) NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
            org_id VARCHAR(36) NOT NULL,
            event_type VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            author_id VARCHAR(36),
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_incident_timeline_incident ON incident_timeline(incident_id);
    """),
    ("incident_hypotheses", """
        CREATE TABLE IF NOT EXISTS incident_hypotheses (
            id VARCHAR(36) PRIMARY KEY,
            incident_id VARCHAR(36) NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
            org_id VARCHAR(36) NOT NULL,
            hypothesis TEXT NOT NULL,
            confidence VARCHAR(20) NOT NULL DEFAULT 'medium',
            status VARCHAR(20) NOT NULL DEFAULT 'investigating',
            evidence TEXT,
            generated_by VARCHAR(20) NOT NULL DEFAULT 'ai',
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_incident_hypotheses_incident ON incident_hypotheses(incident_id);
    """),
    ("incident_similar_incidents", """
        CREATE TABLE IF NOT EXISTS incident_similar_incidents (
            id VARCHAR(36) PRIMARY KEY,
            incident_id VARCHAR(36) NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
            similar_incident_id VARCHAR(36) NOT NULL REFERENCES incidents(id),
            similarity_score NUMERIC(5, 4) NOT NULL,
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_similar_incidents_incident ON incident_similar_incidents(incident_id);
    """),

    # Security scans
    ("security_scans", """
        CREATE TABLE IF NOT EXISTS security_scans (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            product_id VARCHAR(36) REFERENCES products(id),
            repo_name VARCHAR(255) NOT NULL,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            security_score INTEGER,
            summary TEXT,
            scanned_by VARCHAR(36),
            created_at TIMESTAMP DEFAULT now(),
            completed_at TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_security_scans_org ON security_scans(org_id);
    """),
    ("security_findings", """
        CREATE TABLE IF NOT EXISTS security_findings (
            id VARCHAR(36) PRIMARY KEY,
            scan_id VARCHAR(36) NOT NULL REFERENCES security_scans(id) ON DELETE CASCADE,
            org_id VARCHAR(36) NOT NULL,
            scanner VARCHAR(50) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            title VARCHAR(500) NOT NULL,
            description TEXT NOT NULL,
            recommendation TEXT,
            file_path VARCHAR(1024),
            line_number INTEGER,
            cwe_id VARCHAR(20),
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_security_findings_scan ON security_findings(scan_id);
    """),
    ("dependency_alerts", """
        CREATE TABLE IF NOT EXISTS dependency_alerts (
            id VARCHAR(36) PRIMARY KEY,
            scan_id VARCHAR(36) NOT NULL REFERENCES security_scans(id) ON DELETE CASCADE,
            org_id VARCHAR(36) NOT NULL,
            package_name VARCHAR(255) NOT NULL,
            current_version VARCHAR(50),
            vulnerability_id VARCHAR(50),
            severity VARCHAR(20) NOT NULL,
            description TEXT,
            fix_version VARCHAR(50),
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_dependency_alerts_scan ON dependency_alerts(scan_id);
    """),

    # DAST scans
    ("dast_scans", """
        CREATE TABLE IF NOT EXISTS dast_scans (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            product_id VARCHAR(36) REFERENCES products(id),
            target_url VARCHAR(1024) NOT NULL,
            target_env VARCHAR(50) NOT NULL DEFAULT 'staging',
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            summary TEXT,
            risk_score INTEGER,
            scanned_by VARCHAR(36),
            created_at TIMESTAMP DEFAULT now(),
            completed_at TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_dast_scans_org ON dast_scans(org_id);
    """),
    ("dast_findings", """
        CREATE TABLE IF NOT EXISTS dast_findings (
            id VARCHAR(36) PRIMARY KEY,
            scan_id VARCHAR(36) NOT NULL REFERENCES dast_scans(id) ON DELETE CASCADE,
            org_id VARCHAR(36) NOT NULL,
            probe_type VARCHAR(50) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            endpoint VARCHAR(1024) NOT NULL,
            method VARCHAR(10),
            description TEXT NOT NULL,
            evidence TEXT,
            recommendation TEXT,
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_dast_findings_scan ON dast_findings(scan_id);
    """),

    # Business rules
    ("business_rules", """
        CREATE TABLE IF NOT EXISTS business_rules (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            product_id VARCHAR(36) REFERENCES products(id),
            repo_name VARCHAR(255),
            rule_type VARCHAR(50) NOT NULL,
            title VARCHAR(500) NOT NULL,
            description TEXT NOT NULL,
            embedding vector(1536),
            source_file VARCHAR(1024),
            source_lines VARCHAR(50),
            confidence NUMERIC(3, 2),
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_by VARCHAR(36),
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_business_rules_org ON business_rules(org_id);
        CREATE INDEX IF NOT EXISTS idx_business_rules_product ON business_rules(product_id);
        CREATE INDEX IF NOT EXISTS idx_business_rules_embedding
            ON business_rules USING hnsw (embedding vector_cosine_ops)
            WITH (m = 16, ef_construction = 64);
    """),
    ("rule_change_alerts", """
        CREATE TABLE IF NOT EXISTS rule_change_alerts (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            rule_id VARCHAR(36) NOT NULL REFERENCES business_rules(id) ON DELETE CASCADE,
            change_type VARCHAR(50) NOT NULL,
            description TEXT NOT NULL,
            commit_sha VARCHAR(40),
            pr_number INTEGER,
            severity VARCHAR(20) NOT NULL DEFAULT 'medium',
            status VARCHAR(20) NOT NULL DEFAULT 'open',
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_rule_change_alerts_org ON rule_change_alerts(org_id);
        CREATE INDEX IF NOT EXISTS idx_rule_change_alerts_rule ON rule_change_alerts(rule_id);
    """),
    ("rule_simulations", """
        CREATE TABLE IF NOT EXISTS rule_simulations (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            rule_id VARCHAR(36) NOT NULL REFERENCES business_rules(id),
            simulated_by VARCHAR(36) NOT NULL,
            input_values JSONB NOT NULL,
            result JSONB,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_rule_simulations_org ON rule_simulations(org_id);
    """),

    # Impact analysis
    ("impact_analyses", """
        CREATE TABLE IF NOT EXISTS impact_analyses (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            product_id VARCHAR(36) REFERENCES products(id),
            repo_name VARCHAR(255) NOT NULL,
            change_description TEXT NOT NULL,
            risk_level VARCHAR(20),
            summary TEXT,
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            created_by VARCHAR(36),
            created_at TIMESTAMP DEFAULT now(),
            completed_at TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_impact_analyses_org ON impact_analyses(org_id);
    """),
    ("impact_findings", """
        CREATE TABLE IF NOT EXISTS impact_findings (
            id VARCHAR(36) PRIMARY KEY,
            analysis_id VARCHAR(36) NOT NULL REFERENCES impact_analyses(id) ON DELETE CASCADE,
            org_id VARCHAR(36) NOT NULL,
            finding_type VARCHAR(50) NOT NULL,
            severity VARCHAR(20) NOT NULL,
            component VARCHAR(500),
            description TEXT NOT NULL,
            recommendation TEXT,
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_impact_findings_analysis ON impact_findings(analysis_id);
    """),

    # Code generation
    ("code_generations", """
        CREATE TABLE IF NOT EXISTS code_generations (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            user_id VARCHAR(36) NOT NULL,
            request_description TEXT NOT NULL,
            generated_code TEXT,
            language VARCHAR(50),
            model_used VARCHAR(100),
            tokens_used INTEGER,
            cost_usd NUMERIC(12, 8),
            status VARCHAR(20) NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_code_generations_org ON code_generations(org_id);
    """),

    # Executive snapshots
    ("executive_snapshots", """
        CREATE TABLE IF NOT EXISTS executive_snapshots (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            period_start TIMESTAMP NOT NULL,
            period_end TIMESTAMP NOT NULL,
            health_score INTEGER,
            metrics JSONB NOT NULL DEFAULT '{}'::jsonb,
            summary TEXT,
            created_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_executive_snapshots_org ON executive_snapshots(org_id);
    """),

    # Repo docs
    ("repo_docs", """
        CREATE TABLE IF NOT EXISTS repo_docs (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            repo_name VARCHAR(255) NOT NULL,
            doc_type VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            pushed_to_github BOOLEAN NOT NULL DEFAULT false,
            created_by VARCHAR(36),
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_repo_docs_org ON repo_docs(org_id);
    """),
    ("onboarding_progress", """
        CREATE TABLE IF NOT EXISTS onboarding_progress (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            user_id VARCHAR(36) NOT NULL,
            repo_name VARCHAR(255) NOT NULL,
            steps_completed JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMP DEFAULT now(),
            updated_at TIMESTAMP DEFAULT now()
        );
        CREATE INDEX IF NOT EXISTS idx_onboarding_progress_org ON onboarding_progress(org_id);
    """),

    # MCP tokens
    ("mcp_tokens", """
        CREATE TABLE IF NOT EXISTS mcp_tokens (
            id VARCHAR(36) PRIMARY KEY,
            org_id VARCHAR(36) NOT NULL,
            user_id VARCHAR(36) NOT NULL,
            token_hash VARCHAR(255) UNIQUE NOT NULL,
            name VARCHAR(255),
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMP DEFAULT now(),
            last_used_at TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_mcp_tokens_org ON mcp_tokens(org_id);
    """),

    # Migration log (for tracking)
    ("migration_log", """
        CREATE TABLE IF NOT EXISTS migration_log (
            id SERIAL PRIMARY KEY,
            script_name VARCHAR(255) NOT NULL UNIQUE,
            executed_at TIMESTAMP DEFAULT now(),
            success BOOLEAN NOT NULL
        );
    """),
]


def run_migrations(host: str, port: int, database: str, username: str, password: str, ssl_mode: str = "require") -> Generator[dict, None, None]:
    """Executa todas as migrations no banco do cliente via generator (para SSE).

    Yields dicts com:
        {"type": "progress", "step": int, "total": int, "table": str, "status": "ok"|"error", "message": str}
        {"type": "done", "success": bool, "tables_created": int}
    """
    dsn = _build_dsn(host, port, database, username, password, ssl_mode)
    total = len(_OPERATIONAL_TABLES_SQL)
    tables_created = 0

    try:
        eng = create_engine(dsn, pool_pre_ping=True, pool_size=1, max_overflow=0)

        for i, (table_name, sql) in enumerate(_OPERATIONAL_TABLES_SQL):
            try:
                with eng.begin() as conn:
                    conn.execute(text(sql))
                tables_created += 1
                yield {
                    "type": "progress",
                    "step": i + 1,
                    "total": total,
                    "table": table_name,
                    "status": "ok",
                    "message": f"Tabela {table_name} criada",
                }
            except Exception as e:
                yield {
                    "type": "progress",
                    "step": i + 1,
                    "total": total,
                    "table": table_name,
                    "status": "error",
                    "message": str(e),
                }

        eng.dispose()
        yield {"type": "done", "success": True, "tables_created": tables_created}

    except Exception as e:
        yield {"type": "done", "success": False, "tables_created": tables_created, "message": str(e)}


def mark_setup_complete(org_id: str):
    """Marca setup Enterprise como concluido no Supabase."""
    db = SessionLocal()
    try:
        db.execute(text("""
            UPDATE enterprise_db_configs
            SET setup_complete = true, updated_at = now()
            WHERE org_id = :org_id
        """), {"org_id": org_id})
        db.commit()
    finally:
        db.close()


def get_setup_status(org_id: str) -> dict:
    """Retorna status do setup Enterprise."""
    db = SessionLocal()
    try:
        row = db.execute(text("""
            SELECT setup_complete, last_health_status, last_health_check, last_health_error,
                   created_at, updated_at
            FROM enterprise_db_configs
            WHERE org_id = :org_id
        """), {"org_id": org_id}).mappings().first()

        if not row:
            return {"configured": False, "setup_complete": False}

        return {
            "configured": True,
            "setup_complete": row["setup_complete"],
            "last_health_status": row.get("last_health_status"),
            "last_health_check": str(row["last_health_check"]) if row.get("last_health_check") else None,
            "last_health_error": row.get("last_health_error"),
            "created_at": str(row["created_at"]) if row["created_at"] else None,
            "updated_at": str(row["updated_at"]) if row["updated_at"] else None,
        }
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Health Check
# ---------------------------------------------------------------------------

def check_health(org_id: str) -> dict:
    """Testa saude do banco Enterprise e registra resultado.

    Returns:
        {"status": "ok"|"error", "response_time_ms": int, "error": str|None, "previous_status": str|None}
    """
    db = SessionLocal()
    try:
        # Buscar config e status anterior
        row = db.execute(text("""
            SELECT host_encrypted, port, database_name_encrypted, username_encrypted,
                   password_encrypted, ssl_mode, last_health_status
            FROM enterprise_db_configs
            WHERE org_id = :org_id AND setup_complete = true
        """), {"org_id": org_id}).mappings().first()

        if not row:
            return {"status": "error", "response_time_ms": 0, "error": "Config nao encontrada", "previous_status": None}

        previous_status = row.get("last_health_status")
        host = decrypt_api_key(row["host_encrypted"])
        port = row["port"]
        database = decrypt_api_key(row["database_name_encrypted"])
        username = decrypt_api_key(row["username_encrypted"])
        password = decrypt_api_key(row["password_encrypted"])
        ssl_mode = row["ssl_mode"]

        # Testar conexao
        dsn = _build_dsn(host, port, database, username, password, ssl_mode)
        start = time.monotonic()
        error_msg = None
        status = "ok"

        try:
            eng = create_engine(dsn, pool_pre_ping=True, pool_size=1, max_overflow=0,
                                connect_args={"connect_timeout": 10})
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            eng.dispose()
            elapsed = int((time.monotonic() - start) * 1000)
        except Exception as e:
            elapsed = int((time.monotonic() - start) * 1000)
            status = "error"
            error_msg = str(e)

        # Atualizar status no Supabase
        db.execute(text("""
            UPDATE enterprise_db_configs
            SET last_health_check = now(), last_health_status = :status, last_health_error = :error
            WHERE org_id = :org_id
        """), {"status": status, "error": error_msg, "org_id": org_id})

        # Inserir log
        db.execute(text("""
            INSERT INTO enterprise_db_health_log (id, org_id, status, response_time_ms, error_message)
            VALUES (:id, :org_id, :status, :ms, :error)
        """), {"id": str(uuid.uuid4()), "org_id": org_id, "status": status, "ms": elapsed, "error": error_msg})

        db.commit()

        return {
            "status": status,
            "response_time_ms": elapsed,
            "error": error_msg,
            "previous_status": previous_status,
        }
    finally:
        db.close()


def get_health_log(org_id: str, limit: int = 20) -> list[dict]:
    """Retorna historico de health checks."""
    db = SessionLocal()
    try:
        rows = db.execute(text("""
            SELECT status, response_time_ms, error_message, checked_at
            FROM enterprise_db_health_log
            WHERE org_id = :org_id
            ORDER BY checked_at DESC
            LIMIT :limit
        """), {"org_id": org_id, "limit": limit}).mappings().all()

        return [
            {
                "status": r["status"],
                "response_time_ms": r["response_time_ms"],
                "error": r["error_message"],
                "checked_at": str(r["checked_at"]) if r["checked_at"] else None,
            }
            for r in rows
        ]
    finally:
        db.close()


def get_all_enterprise_org_ids() -> list[str]:
    """Retorna org_ids de todas as orgs Enterprise com setup completo."""
    db = SessionLocal()
    try:
        rows = db.execute(text(
            "SELECT org_id FROM enterprise_db_configs WHERE setup_complete = true"
        )).all()
        return [r[0] for r in rows]
    finally:
        db.close()
