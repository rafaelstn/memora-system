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
- `api/deps.py` — FastAPI dependencies: `get_session`, `get_current_user`, `require_role()`
- `api/routes/` — HTTP endpoints:
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
  - `encryption.py` — Fernet encrypt/decrypt/mask for LLM provider API keys
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
- **Multi-tenant**: All queries filter by `org_id` from the authenticated user

## Environment variables

Required in `.env`:
- `DATABASE_URL` — Supabase PostgreSQL connection string
- `OPENAI_API_KEY` — For embeddings (always required)
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWT_SECRET` — Auth

Optional:
- `LLM_ENCRYPTION_KEY` — Fernet key for API key encryption (auto-generated if missing)
- `GITHUB_WEBHOOK_SECRET` — GitHub integration
- `NEXT_PUBLIC_API_URL` — Frontend API base URL (default: `http://localhost:8000`)
- `APP_URL` — Used in notification links (default: `http://localhost:3000`)
- `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`, `SMTP_FROM` — Email notifications

## Test suite

121 tests across 13 test files (all passing):

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

Fixtures in `conftest.py`: `admin_client`, `dev_client`, `suporte_client`, `anon_client` with `_mock_session()` (safe ORM defaults).
