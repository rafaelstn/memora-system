# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What is Memora

Memora is a technical support assistant for Brazilian SMBs. Four main modules:
1. **Code Intelligence** — Indexes codebases via AST chunking, stores embeddings in pgvector, answers questions in Portuguese using hybrid search (semantic + BM25 with RRF fusion)
2. **Error Monitor** — Receives logs from external systems, analyzes with AI, generates alerts with explanations in Portuguese, and notifies via email/webhooks
3. **Technical Memory** — Captures and organizes technical knowledge from PRs, commits, issues, documents, and manual ADRs. Generates per-component wikis. Integrates with chat as additional context.
4. **Code Review** — Automatically reviews PRs via GitHub webhook and accepts manual code reviews. Analyzes bugs, security, performance, consistency, and patterns using 5 parallel LLM calls. Posts formatted comments on GitHub PRs.

Multi-provider LLM support (OpenAI, Anthropic, Google, Groq, Ollama) with per-organization configuration.

## Commands

### Backend (Python/FastAPI)
```bash
# Run API locally
uvicorn app.main:app --reload

# Run all tests
python -m pytest tests/ -v

# Run a single test file
python -m pytest tests/test_auth.py -v

# Lint
ruff check app/ tests/
ruff format app/ tests/
```

### Frontend (Next.js 16)
```bash
cd frontend
npm run dev      # dev server on :3000
npm run build    # production build
npm run lint     # eslint
```

### Docker (full stack)
```bash
docker compose up --build       # start both services
docker compose down             # stop
docker compose build memora-api # rebuild backend only
```

### Database scripts
```bash
python scripts/setup_tables.py              # create all tables (incl. organizations, monitor, knowledge)
python scripts/migrate_add_password_hash.py  # add password_hash column
python scripts/migrate_add_llm_providers.py  # create llm_providers table
python scripts/migrate_add_orgs.py           # add organizations + org_id columns
python scripts/migrate_add_monitor.py        # create monitor tables
python scripts/migrate_add_knowledge.py      # create knowledge tables
python scripts/migrate_add_code_reviews.py   # create code review tables
python scripts/seed_admin.py                 # create admin user
python scripts/index_repo.py /path repo-name # index a repository
python scripts/check_connection.py           # verify DB connectivity
```

### Agent (Error Monitor)
```bash
cd agent
cp config.yaml.example config.yaml  # edit with your token
python memora_agent.py --config config.yaml
# Or install as service:
sudo bash install.sh       # Linux (systemd)
powershell install.ps1     # Windows (Task Scheduler)
```

## Architecture

**Two services**: `memora-api` (FastAPI on :8000) and `memora-web` (Next.js on :3000). Both run in Docker with an IPv6-enabled network for Supabase connectivity.

### Backend structure (`app/`)
- `main.py` — FastAPI app, CORS, router registration
- `config.py` — Pydantic Settings (all config via env vars / `.env`)
- `api/deps.py` — FastAPI dependencies: `get_session` (Supabase), `get_data_session` (SaaS/Enterprise router), `get_current_user`, `require_role()`, `get_current_product()`
- `api/routes/` — HTTP endpoints:
  - `enterprise.py` — Enterprise DB setup: test-connection, setup (SSE), status
  - `products.py` — CRUD products, membership management (admin only for write ops)
  - `auth.py` — Login, register (invite-based with org creation), /me
  - `ask.py`, `ask_stream.py` — Question answering (sync + SSE streaming with provider_id)
  - `ingest.py` — Repository ingestion (sync + SSE streaming)
  - `conversations.py` — CRUD conversations/messages
  - `admin.py` — Metrics, users, invites, repos (list + delete)
  - `users.py` — User search, add-by-email
  - `integrations.py` — GitHub connect/disconnect/repos
  - `llm_providers.py` — CRUD providers, test, set-default, test-connection, /active
  - `webhooks.py` — GitHub webhook for auto re-indexation + PR review triggers
  - `logs_ingest.py` — POST /api/logs/ingest (project token auth, batch support)
  - `monitor.py` — Monitor CRUD: projects, alerts, logs, webhooks
  - `knowledge.py` — Knowledge CRUD: search, entries, timeline, ADRs, documents, wiki, sync
  - `reviews.py` — Code Review: manual review, list, detail, stats, delete
- `core/` — Business logic:
  - `auth.py` — JWT tokens (python-jose) + bcrypt password hashing
  - `chunker.py` — AST-based Python file chunking
  - `embedder.py` — OpenAI embeddings with tiktoken token counting
  - `search.py` — Hybrid search: pgvector cosine + tsvector/tsquery, RRF fusion (k=60)
  - `assistant.py` — LLM orchestration, model selection (fast vs deep)
  - `ingestor.py` — Repository ingestion pipeline (clone/pull → chunk → embed → store)
  - `encryption.py` — Fernet encrypt/decrypt/mask for LLM provider API keys and Enterprise DB credentials
  - `enterprise_db.py` — Enterprise DB management: test connection, run migrations (SSE), engine cache, session factory
  - `log_analyzer.py` — AI-powered log analysis (uses LLM router, fallback on failure)
  - `notifier.py` — Email (SMTP) + webhook notifications for alerts
  - `knowledge_extractor.py` — GitHub PR/commit/issue extraction with LLM analysis
  - `document_processor.py` — PDF/DOCX/MD/TXT text extraction and indexing
  - `wiki_generator.py` — AI-powered per-component wiki generation
  - `code_reviewer.py` — AI-powered code review (5 parallel category analyses)
  - `github_commenter.py` — Posts formatted review comments on GitHub PRs
- `integrations/` — External clients:
  - `llm_router.py` — DB-based LLM router (complete, stream, test_provider, test_connection_raw)
  - `llm_clients/` — Per-provider clients (openai, anthropic, google, groq, ollama) + pricing
  - `github_client.py` — Clone/pull repos
- `models/` — SQLAlchemy models:
  - `chunk.py` — CodeChunk + Base
  - `user.py` — User
  - `organization.py` — Organization
  - `product.py` — Product, ProductMembership
  - `conversation.py` — Conversation, Message, Invite
  - `llm_provider.py` — LLMProvider
  - `monitor.py` — MonitoredProject, LogEntry, ErrorAlert, AlertWebhook
  - `knowledge.py` — KnowledgeEntry, KnowledgeDocument, KnowledgeWiki
  - `code_review.py` — CodeReview, ReviewFinding
- `db/session.py` — Engine + session factory (sslmode=require for Supabase)

### Frontend structure (`frontend/src/`)
- `app/` — Next.js App Router pages:
  - `chat/[repo]/` — Chat interface (3 columns)
  - `dashboard/` — Repos list, admin (metrics, users), settings
  - `dashboard/monitor/` — Error monitor main page
  - `dashboard/monitor/[projectId]/` — Project detail (alerts, logs, config tabs)
  - `dashboard/monitor/alerts/` — Global alerts page with filters + CSV export
  - `dashboard/memory/` — Technical Memory: search, timeline, wiki, ADRs, documents
  - `dashboard/reviews/` — Code Review: list with stats, manual review modal
  - `dashboard/reviews/[id]/` — Review detail with findings by category
  - `auth/` — Signin, update-password
  - `invite/[token]/` — Invite acceptance
- `components/` — React components:
  - `chat/` — ChatPanel, ChatSidebar, MessageBubble, SourcesPanel, ChatInput, ModelSelector
  - `settings/` — LLMProvidersSection
  - `layout/` — DashboardSidebar (with Monitor link for admin/dev)
  - `ui/` — Badge, Modal, Skeleton
- `lib/` — API client (api.ts), auth (auth.ts), types (types.ts), hooks, utils

### Agent (`agent/`)
- `memora_agent.py` — Standalone Python script: tails log files, parses multiple formats, sends batches to Memora
- `config.yaml.example` — Configuration template
- `install.sh` / `install.ps1` — Service installers (systemd / Windows Task Scheduler)

## Auth system

JWT-based with role-based access control. Three roles: `admin`, `dev`, `suporte`.

- **Public routes**: `/api/health`, `/api/health/admin-exists`, `/api/auth/login`, `/api/auth/register`
- **Any authenticated user**: `/api/ask`, `/api/ask/stream`, `/api/conversations`, `/api/repos`, `/api/llm-providers/active`, `/api/knowledge/search`
- **admin + dev**: `/api/ingest`, `/api/ingest/stream`, `/api/monitor/*`, `/api/knowledge/*` (CRUD, sync, wiki, ADRs, documents), `/api/reviews/*` (code review)
- **admin only**: `/api/admin/*`, `/api/llm-providers` (CRUD), `/api/integrations/github`
- **Project token auth**: `/api/logs/ingest` (no JWT, uses project-specific token)

Registration: first user creates org + becomes admin. Subsequent users require invite (inherits org_id).

## Product hierarchy (Org → Product)

Multi-tenant data isolation now uses a two-level hierarchy: **Organization → Product**.

- **Model**: `app/models/product.py` — `Product` (id, org_id, name, description, is_active) + `ProductMembership` (product_id, user_id, unique constraint)
- **Dependency**: `get_current_product()` in `app/api/deps.py` — resolves product from header `X-Product-ID` or query param `product_id`
- **Access control**: Admin has access to all products in org. Dev/suporte need explicit membership via `product_memberships` table
- **Data filtering**: All data routes (repos, conversations, chunks, monitors, reviews, knowledge, rules, impact, security, etc.) filter by `product_id` instead of `org_id`
- **Config routes**: Admin-global routes (`/api/admin/*`, `/api/llm-providers`) continue filtering by `org_id`
- **Routes**: `app/api/routes/products.py` — CRUD products (admin), membership management (admin), list products (filtered by role)
- **Migration**: `scripts/migrate_add_products.py` — creates tables, adds `product_id` column to 10 data tables, creates "Produto Principal" per org, migrates existing data
- **Tables with product_id**: code_chunks, conversations, monitored_projects, code_reviews, code_generations, knowledge_entries, business_rules, impact_analyses, security_scans, dast_scans

## Enterprise mode (SaaS vs Enterprise)

Organizations have a `mode` field: `saas` (default) or `enterprise`.

- **SaaS**: All data in Supabase (default behavior)
- **Enterprise**: Auth/billing/config in Supabase, operational data in client's external PostgreSQL

### Session routing

Two session dependencies in `app/api/deps.py`:

- **`get_session`** → Always returns Supabase session. Used by: `auth.py`, `admin.py`, `llm_providers.py`, `enterprise.py`, `onboarding.py`, `notifications.py`, `integrations.py`, `health_admin.py`, `users.py`
- **`get_data_session`** → Returns Supabase for SaaS, client DB for Enterprise. Used by: all operational routes (`ask`, `conversations`, `monitor`, `incidents`, `knowledge`, `reviews`, `docs`, `rules`, `codegen`, `impact`, `security`, `executive`, `products`, `ingest`, `logs_ingest`)

### Enterprise setup flow

1. Admin creates org with `mode = 'enterprise'`
2. Admin sees `/setup/enterprise` with DB config form
3. `POST /api/enterprise/test-connection` validates credentials
4. `POST /api/enterprise/setup` saves encrypted credentials + runs migrations via SSE
5. All operational tables created in client's DB (same schema, no FK to Supabase tables)
6. `enterprise_db_configs.setup_complete = true`

### Key files

- `app/core/enterprise_db.py` — Connection testing, migration runner, engine cache, session factory
- `app/api/routes/enterprise.py` — Setup routes (test-connection, setup SSE, status)
- `scripts/migrate_add_enterprise.py` — Creates `enterprise_db_configs` table + `mode` column on organizations
- `frontend/src/app/setup/enterprise/page.tsx` — Setup wizard UI

### Engine caching

Enterprise DB engines are cached in memory (`_engine_cache` dict in `enterprise_db.py`). Cache is invalidated when credentials are updated via `invalidate_engine_cache(org_id)`.

### Tests

All test fixtures override BOTH `get_session` AND `get_data_session` to ensure operational routes work with mocked sessions.

## LLM provider system

Multi-provider LLM support managed via database (`llm_providers` table), not env vars.

- **Providers**: OpenAI, Anthropic, Google, Groq, Ollama
- **API key security**: Fernet encryption (`app/core/encryption.py`). Auto-generates key if `LLM_ENCRYPTION_KEY` not set
- **Test connection**: `POST /api/llm-providers/test-connection` tests with raw credentials (no DB needed)
- **Frontend**: ModelSelector dropdown in chat header (dev/admin), fixed label for suporte

## Error Monitor system

Logs arrive via POST /api/logs/ingest (project token auth) or via the agent.

- **Analysis**: `log_analyzer.py` sends error/critical logs to LLM for analysis, creates structured alerts
- **Notifications**: `notifier.py` emails org admins + POSTs to configured webhooks
- **Frontend**: Dashboard at `/dashboard/monitor` with project list, alert detail drawer, log feed (5s polling)
- **Agent**: `agent/memora_agent.py` — tail files, parse formats (Python logging, Loguru, JSON, Nginx, plain text), batch send

## Technical Memory system

Captures and organizes technical knowledge from GitHub (PRs, commits, issues), uploaded documents, and manual ADRs.

- **Extraction**: `knowledge_extractor.py` fetches from GitHub API, sends to LLM for analysis in Portuguese, saves with embeddings
- **Documents**: `document_processor.py` extracts text from PDF/DOCX/MD/TXT, generates summaries via LLM
- **Wiki**: `wiki_generator.py` combines code chunks + knowledge history to generate per-component wikis with 6 sections
- **Search**: Hybrid search (semantic + full-text with RRF) across knowledge_entries
- **Chat integration**: `ask_stream.py` searches knowledge_entries in parallel with code_chunks, adds to LLM context
- **Frontend**: `/dashboard/memory` with 5 tabs: Search, Timeline, Wiki, ADRs, Documents

## Database tables

- `products` — Products within orgs (name, description, is_active, org_id)
- `product_memberships` — User membership in products (product_id, user_id, unique constraint)
- `organizations` — Multi-tenant orgs (name, slug, settings)
- `users` — Users with role, org_id, github_connected
- `code_chunks` — Indexed code with pgvector embeddings (HNSW index), org_id
- `conversations` — Chat conversations per repo per user, org_id
- `messages` — Chat messages with model_used, cost_usd, tokens_used
- `invites` — Invite tokens with role, email, expiry, org_id
- `llm_providers` — LLM provider configs with encrypted API keys
- `github_integration` — GitHub OAuth tokens, org_id
- `monitored_projects` — Projects being monitored (token-based auth)
- `log_entries` — Received log entries (level, message, source, stack_trace, metadata)
- `error_alerts` — AI-generated alerts (title, explanation, severity, suggested_actions, status)
- `alert_webhooks` — Webhook URLs for alert notifications
- `knowledge_entries` — Technical knowledge (PRs, commits, issues, documents, ADRs) with pgvector embeddings
- `knowledge_documents` — Uploaded documents (PDF, DOCX, MD, TXT) with processing status
- `knowledge_wikis` — AI-generated per-component wikis
- `code_reviews` — Code reviews (PR + manual) with score, verdict, summary
- `review_findings` — Individual findings per review (category, severity, suggestion)
- `refresh_tokens` — JWT refresh tokens (token_hash PK, user_id, family_id, expires_at, used_at, revoked_at)
- `audit_log` — Security audit trail (org_id, user_id, action, resource_type, resource_id, detail, ip_address)
- `weekly_digest_log` — Weekly digest send history (org_id, product_ids, week_start, week_end, status, details)
- `proactive_notifications_log` — Proactive notification log (org_id, notification_type, channel, detail, resolved_at)
- `executive_weekly_snapshots` — Weekly executive metrics (security_score, error_count, support_questions, code_review_score, etc.)
- `data_exports` — Export job tracking (org_id, format, status, file_path, expires_at)
- `org_plans` — Plan and trial tracking per org (plan type, trial dates, is_active, activated_by, notes)
- `plan_contacts` — Upgrade contact requests (org_id, user_id, contact_reason, message, is_read)

## Plan & Trial system

Organization plan management with 7-day trial for new orgs.

- **Plans**: `pro_trial` (7-day trial), `pro` (paid), `enterprise` (client infra), `customer` (custom)
- **Auto-creation**: New org registration auto-creates `pro_trial` with 7-day trial
- **Enforcement**: `PlanEnforcementMiddleware` in main.py returns 402 on expired/inactive plans
- **Exempt routes**: auth, health, enterprise setup, plan management, webhooks, log ingest
- **Dependencies**: `get_current_plan()` and `require_active_plan()` in deps.py
- **Routes**: `app/api/routes/plans.py` — GET status, POST contact, master admin CRUD
- **Master admin**: `MASTER_ADMIN_EMAIL` env var controls who can manage all plans
- **Frontend**: Trial banner (7-4d blue, 3-1d yellow, expired red), /upgrade page, admin planos panel
- **Migration**: `scripts/migrate_add_plans.py`

## Weekly Digest system

Automated weekly email digest sent every Monday 08h BRT to org admins.

- **Generator**: `app/core/digest_generator.py` — collects metrics from all modules (suporte, monitor, reviews, memory, security), renders HTML email, sends via SMTP
- **Scheduler**: `app/core/scheduler.py` — thread-based scheduler, runs digest Monday 11h UTC (08h BRT), proactive checks daily 12h UTC (09h BRT)
- **Route**: `POST /api/admin/digest/send-now` — admin-only manual trigger
- **Migration**: `scripts/migrate_add_digest_notifications.py`

## Proactive Notifications system

Automated checks that create dashboard banners and send emails when conditions are met.

- **Triggers**: repo_outdated (>7d), rules_changed (3+), dev_inactive (3-7d no activity), critical_alerts (5+ unresolved >48h)
- **Cooldown**: 7-day per type per org (prevents spam)
- **Notifier**: `app/core/proactive_notifier.py` — check functions, banner CRUD, orchestrator
- **Routes**: `GET /api/notifications/banners`, `POST /api/notifications/banners/{id}/dismiss`
- **Frontend**: `components/layout/notification-banners.tsx` — polls every 5min, max 3 visible, dismiss with optimistic UI
- **Dashboard**: banners rendered below EnterpriseDBBanner in dashboard layout

## Global Search system

Cross-module search with Cmd+K (Mac) / Ctrl+K (Windows) shortcut.

- **Backend**: `app/core/global_search.py` — searches 8 sources (conversations, business_rules, knowledge_entries, repo_docs, review_findings, security_findings, error_alerts, knowledge_wikis)
- **Route**: `GET /api/search/global?q={query}&limit=5` — hybrid search (semantic + full-text), grouped by source
- **Frontend**: `components/search/GlobalSearch.tsx` — command palette modal, debounce 300ms, keyboard navigation, recent searches
- **Security**: security_findings hidden from suporte role; per-source error isolation
- **Contextual**: `components/shared/RelatedContent.tsx` — collapsible related content section + "Ask assistant" button
- **Chat prefill**: `?context=` URL param pre-fills ChatInput (no auto-submit)

## Executive History system

Weekly metric snapshots for trend analysis.

- **Generator**: `app/core/executive_weekly.py` — calculates 7 metrics (security score, error count, support questions, code review score, PRs reviewed, incident resolution time, doc coverage)
- **Scheduler**: runs Monday 03h UTC (00h BRT), saves snapshot per org/product
- **Routes**: `GET /api/executive/history?period=4w|3m|6m`, `GET /api/executive/history/csv`, `POST /api/executive/history/generate-now`
- **Frontend**: `components/executive/ExecutiveHistory.tsx` — recharts sparklines, period selector, metric checkboxes, comparative table, CSV export
- **Migration**: `scripts/migrate_add_executive_weekly.py`

## Data Export system

Full data export for admin users (JSON or CSV ZIP).

- **Exporter**: `app/core/data_exporter.py` — exports 13 tables, excludes sensitive data (passwords, API keys, tokens)
- **Routes**: `POST /api/admin/exports`, `GET /api/admin/exports`, `GET /api/admin/exports/{id}/download`
- **Background**: runs as FastAPI BackgroundTask, email notification on completion
- **Cleanup**: scheduler deletes expired files daily (02h BRT), 7-day expiry
- **Frontend**: `/dashboard/admin/exportar` — export buttons, period selector, history table with polling
- **Migration**: `scripts/migrate_add_data_exports.py`

## Code Review system

Automatic PR review via GitHub webhook + manual code review via dashboard.

- **Analysis**: `code_reviewer.py` runs 5 parallel LLM calls (bugs, security, performance, consistency, patterns), calculates score/verdict
- **GitHub comments**: `github_commenter.py` posts formatted markdown comment on PR with findings
- **Score**: Starts at 100, deducts by severity (critical: -25, high: -15, medium: -8, low: -3, info: -1)
- **Verdict**: approved (≥85, no critical/high), approved_with_warnings (≥70, no critical), needs_changes (≥50 or high), rejected (<50 or critical)
- **Webhook**: `webhooks.py` handles `pull_request` events (opened, synchronize, reopened)
- **Settings**: `organizations.settings.code_review` — auto_review, min_comment_severity, custom_instructions
- **Frontend**: `/dashboard/reviews` (list + stats + manual modal), `/dashboard/reviews/[id]` (detail with findings)

## Key conventions

- **Language**: All responses, comments, and UI text in Brazilian Portuguese
- **Database**: Supabase PostgreSQL (remote, IPv6-only). No Alembic — migrations are standalone scripts in `scripts/`
- **Embeddings**: Always OpenAI `text-embedding-3-small` (1536 dims)
- **Vector queries**: Use `CAST(:embedding AS vector)` syntax, not `::vector`
- **Password hashing**: Use `bcrypt` directly (not `passlib`)
- **Tests**: Mock DB sessions via FastAPI dependency overrides (`tests/conftest.py`), not `@patch` on `get_session`
- **SSE streaming**: Chat responses stream via Server-Sent Events on `/api/ask/stream`
- **Multi-tenant**: Data queries filter by `product_id` (via `get_current_product` dependency). Config queries (LLM providers, admin) filter by `org_id`. All data routes require `X-Product-ID` header or `product_id` query param

## Environment variables

Required in `.env`:
- `DATABASE_URL` — Supabase PostgreSQL connection string
- `OPENAI_API_KEY` — For embeddings (always required)
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` — Auth

Optional:
- `LLM_ENCRYPTION_KEY` — Fernet key for API key encryption (**mandatory in production**, auto-generated only in dev/test)
- `GITHUB_WEBHOOK_SECRET` — GitHub integration
- `NEXT_PUBLIC_API_URL` — Frontend API base URL (default: `http://localhost:8000`)
- `APP_URL` — Used in notification links (default: `http://localhost:3000`)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` — Email notifications
- `MASTER_ADMIN_EMAIL` — Email of master admin for plan management (Rafael)

## Security hardening

### Rate limiting (slowapi)
- Centralized in `app/core/rate_limit.py` with `Limiter(key_func=get_remote_address)`
- Per-route limits: AUTH 10/min, REGISTER 5/min, ASK 60/min, INGEST 10/min, DEFAULT 120/min
- Handler returns 429 with Portuguese message

### JWT refresh tokens
- `app/core/refresh_tokens.py` — SHA-256 hashed, 7-day expiry, family-based rotation
- Replay attack detection: reused token revokes entire family
- Routes: `POST /auth/refresh` (rotation), `POST /auth/logout` (revocation)
- Migration: `scripts/migrate_add_refresh_tokens.py`

### Encryption
- `LLM_ENCRYPTION_KEY` mandatory in production (SystemExit if missing)
- `validate_encryption_key()` called on startup (non-dev/test)
- Pre-deploy check: `scripts/pre_deploy_check.py`

### Security headers (FastAPI + Next.js)
- `SecurityHeadersMiddleware` in `app/main.py`: X-Content-Type-Options, X-Frame-Options, X-XSS-Protection, Referrer-Policy, Permissions-Policy, HSTS (prod only)
- `next.config.ts`: CSP (default-src self, frame-ancestors none), same headers

### Payload size limits
- `PayloadSizeLimitMiddleware` in `app/main.py`: 1MB chat, 50MB ingest/upload, 10MB default
- Returns 413 with Portuguese message

### Repo ingestion validation
- `_check_github_repo_size()` — GitHub API size check before cloning (max 500MB)
- `_check_local_repo_size()` — Walk check (max 500MB / 50K files)
- Returns 400 with clear message before wasting resources

### DAST SSRF prevention
- `_is_blocked_host()` — Blocks private/loopback/link-local/reserved IPs + localhost variants
- DNS resolution check for domains that resolve to private IPs
- `validate_target_scope()` — Org-scoped target validation (repos, projects, previous scans)

### Audit log
- Table: `audit_log` (org_id, user_id, action, resource_type, resource_id, detail, ip_address)
- Service: `app/core/audit.py` — `log_action()` (never raises), `get_audit_log()` (filtered)
- Route: `GET /api/admin/audit` (admin only, paginated, filterable)
- Migration: `scripts/migrate_add_audit_log.py`

### X-Product-ID validation
- `get_current_product()` in `deps.py` validates product belongs to user's org
- Admin: access to all org products. Dev/suporte: require explicit membership

## Test suite

459 tests across multiple test files (all passing):

- `test_api_endpoints.py` — Health, ask, ingest, conversations
- `test_auth.py` — JWT, registration, role guards, /me
- `test_assistant.py` — Deep reasoning detection
- `test_chunker.py` — AST chunking
- `test_embedder.py` — Embedding dimensions, batching, cost
- `test_search.py` — RRF fusion
- `test_webhooks.py` — GitHub webhook signature validation
- `test_integration_github.py` — GitHub connect/disconnect
- `test_llm_providers.py` — CRUD, validation, roles, encryption, test-connection
- `test_monitor.py` — Log ingest, alerts, projects, webhooks, notifications
- `test_log_analyzer.py` — AI analysis, parsing, fallback
- `test_knowledge.py` — ADRs, search, entries, timeline, documents, wiki, extraction parsing
- `test_code_review.py` — Manual review, list, stats, findings parsing, score/verdict, GitHub comment, webhook PR events
- `test_products.py` — CRUD products, membership, access control, product guards, get_current_product dependency
- `test_security.py` — Rate limiting, security headers, payload limits, refresh tokens (create, rotate, replay, revoke), audit log, encryption validation, DAST SSRF prevention, repo size validation
- `test_digest_notifications.py` — Digest generation, empty week skip, email rendering, merge, send-now route (admin/dev/suporte), proactive triggers (repo_outdated, rules_changed, dev_inactive, critical_alerts), cooldown, banners CRUD, dismiss, scheduler checks
- `test_global_search.py` — Multi-source search, security role filtering, source failure isolation, route validation, truncation
- `test_executive_weekly.py` — Snapshot generation, empty data, DB errors, history period filter, CSV export, route permissions, scheduler
- `test_data_export.py` — JSON/CSV export file creation, sensitive data exclusion, cleanup expired, route permissions, scheduler cleanup
- `test_plans.py` — Trial active/expired, plan statuses (pro/enterprise/customer/inactive), require_active_plan guard, plan routes, master admin CRUD, contact submission, registration auto-creates trial

Fixtures in `conftest.py`: `admin_client`, `dev_client`, `suporte_client`, `anon_client` with `_mock_session()` and `_fake_product()` (safe ORM defaults).
