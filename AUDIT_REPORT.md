# Auditoria Interna — Memora v0.2.0

**Data:** 2026-03-07
**Escopo:** Repositorio completo (backend, frontend, testes, configuracao, infraestrutura)
**Objetivo:** Identificar problemas reais antes do produto ser considerado solido

---

## Resumo Executivo

O Memora esta funcional e com boa cobertura de testes (299+ testes passando), mas apresenta problemas que precisam ser resolvidos antes de ir para producao. Os mais criticos envolvem **seguranca** (chave de criptografia logada, CORS hardcoded, org_id opcional em funcoes internas) e **qualidade de codigo** (memory leaks no frontend, error handling silencioso, polling sem cleanup).

| Severidade | Backend | Frontend | Testes/Config | Total |
|------------|---------|----------|---------------|-------|
| **Critico** | 2 | 1 | 1 | **4** |
| **Alto** | 5 | 8 | 5 | **18** |
| **Medio** | 8 | 12 | 6 | **26** |
| **Baixo** | 4 | 2 | 3 | **9** |
| **Total** | **19** | **23** | **15** | **57** |

---

## 1. Problemas Criticos

### C-01: Chave de criptografia logada em texto plano
- **Arquivo:** `app/core/encryption.py:19-22`
- **Descricao:** Quando `LLM_ENCRYPTION_KEY` nao esta configurada, o sistema gera uma chave temporaria e loga ela em texto plano via `logger.warning()`. Em producao, essa chave apareceria nos logs do servidor, expondo todas as API keys criptografadas.
- **Impacto:** Comprometimento de todas as chaves de API dos provedores LLM
- **Fix:** Remover a chave do log. Logar apenas que foi gerada, sem o valor.

### C-02: CORS hardcoded para localhost
- **Arquivo:** `app/main.py:28-33`
- **Descricao:** `allow_origins` aceita apenas `localhost:3000` e `127.0.0.1:3000`. Em producao, o frontend tera outro dominio e as requisicoes serao bloqueadas. Nao ha configuracao via env var.
- **Impacto:** Aplicacao quebra em qualquer ambiente que nao seja local
- **Fix:** Mover origins para `settings.allowed_origins` (env var `CORS_ORIGINS`)

### C-03: Token JWT acessado via localStorage direto no frontend
- **Arquivo:** `frontend/src/app/dashboard/impact/page.tsx:66`
- **Descricao:** A pagina de Impact usa `localStorage.getItem("memora_token")` diretamente em vez de `getAccessToken()` da lib/auth.ts. Inconsistente com o resto da aplicacao e bypassa qualquer logica de refresh/validacao.
- **Impacto:** Risco de seguranca se houver XSS; padrao inconsistente
- **Fix:** Substituir por `getAccessToken()` e usar a funcao de API centralizada

### C-04: Helpers de teste duplicados em 10+ arquivos
- **Arquivo:** `tests/test_pdf.py`, `test_onboarding.py`, `test_health_admin.py`, `test_incidents.py`, `test_email.py`, `test_docs.py`, etc.
- **Descricao:** `_fake_user()` esta copiada identicamente em pelo menos 10 arquivos de teste em vez de ser importada do `conftest.py`. Qualquer mudanca no modelo User (novo campo obrigatorio, renomeacao) exige alterar 10+ arquivos.
- **Impacto:** Manutencao fragil; risco alto de testes quebrando em cadeia
- **Fix:** Mover `_fake_user()` para `conftest.py` e importar em todos os testes

---

## 2. Problemas Altos

### A-01: org_id opcional em _clear_repo_chunks
- **Arquivo:** `app/core/ingestor.py:49-61`
- **Descricao:** A funcao `_clear_repo_chunks()` aceita `org_id=None` e, nesse caso, deleta chunks de TODAS as organizacoes para aquele repo. Isso viola o principio de multi-tenancy.
- **Fix:** Tornar `org_id` obrigatorio (sem valor default)

### A-02: SQL dinamico com f-string em 5 rotas
- **Arquivos:**
  - `app/api/routes/monitor.py:250` — `text(f"UPDATE error_alerts SET {updates} ...")`
  - `app/api/routes/llm_providers.py:208` — `text(f"UPDATE llm_providers SET {', '.join(updates)} ...")`
  - `app/api/routes/incidents.py:473` — `text(f"UPDATE incidents SET {', '.join(updates)} ...")`
  - `app/api/routes/rules.py:109,118` — `text(f"SELECT ... WHERE {where} ...")`
  - `app/api/routes/impact.py:128` — mesmo padrao
- **Descricao:** Embora os valores sejam parametrizados (`:param`), os nomes de colunas sao construidos via f-string. Hoje os nomes vem de codigo controlado, mas o padrao e fragil — qualquer refatoracao futura que aceite nomes de campos do request pode introduzir SQL injection.
- **Fix:** Criar um helper `build_update_query()` que valide os campos contra uma whitelist explicita

### A-03: Chave de criptografia efemera sem persistencia
- **Arquivo:** `app/core/encryption.py:17-18`
- **Descricao:** Se `LLM_ENCRYPTION_KEY` nao esta no `.env`, uma chave temporaria e gerada em memoria. Ao reiniciar o servidor, uma nova chave e gerada e todas as API keys previamente criptografadas ficam irrecuperaveis.
- **Fix:** Falhar com erro explicito se a chave nao estiver configurada, em vez de gerar uma temporaria

### A-04: Memory leaks em polling no frontend (6 ocorrencias)
- **Arquivos:**
  - `frontend/src/app/dashboard/docs/[repoName]/page.tsx:124-137` — setInterval sem cleanup no unmount
  - `frontend/src/app/dashboard/metrics/security-tab.tsx:85-97,260-275` — 2 polling sem cleanup
  - `frontend/src/app/dashboard/impact/page.tsx:100-117` — setInterval sem cleanup + multiplos polls simultaneos
  - `frontend/src/app/dashboard/executive/page.tsx:166-167` — polling sem cleanup
  - `frontend/src/app/dashboard/codegen/page.tsx:123` — setTimeout sem ref
- **Descricao:** `setInterval` e `setTimeout` criados em handlers de clique ou useEffect sem retorno de cleanup. Se o usuario navegar para outra pagina durante o polling, as requisicoes continuam em background.
- **Fix:** Usar `useRef` para armazenar IDs e adicionar cleanup em `useEffect` return ou verificar `isMounted` ref

### A-05: Error handling silencioso em 15+ catch blocks no frontend
- **Arquivos:** `impact/page.tsx:82,118`, `codegen/page.tsx:73-74,129,170`, `docs/[repoName]/page.tsx:100,106,112`, `memory/page.tsx:85`, `auth/signin/page.tsx:68,111`, `auth/update-password/page.tsx:35`, `admin/metrics/page.tsx`
- **Descricao:** Blocos `catch { /* */ }` ou `.catch(() => {})` que engolem erros sem feedback ao usuario. Particularmente grave em auth (login/reset senha) onde o usuario fica sem saber por que a operacao falhou.
- **Fix:** Adicionar `toast.error()` com mensagem generica nos catches criticos; pelo menos `console.error()` nos demais

### A-06: Dependencias sem upper bound em pyproject.toml
- **Arquivo:** `pyproject.toml:6-30`
- **Descricao:** Todas as dependencias usam `>=` sem limite superior. `fastapi>=0.115` poderia instalar FastAPI 1.0 (breaking changes), `anthropic>=0.43` poderia instalar v1.0, etc.
- **Fix:** Usar `~=` (compatible release) ou definir upper bounds: `fastapi>=0.115,<1.0`

### A-07: Docker rodando em modo dev
- **Arquivos:** `Dockerfile.api` (CMD com `--reload`), `frontend/Dockerfile` (`npm run dev`)
- **Descricao:** As imagens Docker executam em modo de desenvolvimento com hot-reload habilitado. Nao e adequado para producao (performance, seguranca, file watching desnecessario).
- **Fix:** Criar configuracoes separadas para dev/prod ou usar env var para controlar o modo

### A-08: Sem health checks no docker-compose.yml
- **Arquivo:** `docker-compose.yml`
- **Descricao:** Nenhum servico tem `healthcheck` configurado. O frontend depende do backend (`depends_on: memora-api`) mas sem condicao de saude — pode iniciar antes do backend estar pronto.
- **Fix:** Adicionar healthcheck usando `/api/health` para o backend

---

## 3. Problemas Medios

### M-01: Mensagens listadas sem filtro org_id
- **Arquivo:** `app/api/routes/conversations.py:87-89`
- **Descricao:** A query de mensagens filtra apenas por `conversation_id`, sem `org_id`. A conversa e validada antes (linha 80-82), mas a query de mensagens em si nao tem a protecao de multi-tenancy.
- **Fix:** Adicionar `AND org_id = :org_id` ou fazer JOIN com conversations

### M-02: Cache JWKS sem TTL
- **Arquivo:** `app/core/auth.py:10-31`
- **Descricao:** `_jwks_cache` e um dicionario global sem estrategia de invalidacao. Se o Supabase rotacionar as chaves, o sistema continuara usando as antigas ate reiniciar.
- **Fix:** Adicionar TTL (ex: 1h) ou re-fetch em caso de falha de validacao

### M-03: Fernet como singleton global mutavel
- **Arquivo:** `app/core/encryption.py:9,12-25`
- **Descricao:** `_fernet` e uma variavel global mutada via `global _fernet`. Funciona pelo GIL, mas dificulta testabilidade e pode causar problemas com multi-process workers.
- **Fix:** Usar um pattern tipo lazy property ou functools.lru_cache

### M-04: MAIN_BRANCHES hardcoded
- **Arquivo:** `app/api/routes/webhooks.py:23`
- **Descricao:** Apenas `main` e `master` sao reconhecidos. Repositorios com `develop`, `staging` ou branches customizadas nao disparam re-indexacao ou code review.
- **Fix:** Tornar configuravel via `organizations.settings`

### M-05: SessionLocal() em background tasks
- **Arquivos:** `logs_ingest.py:106`, `reviews.py:39`, `docs.py:41`, `rules.py:35`, `incidents.py`
- **Descricao:** Background tasks criam conexoes via `SessionLocal()` direto, sem pool management centralizado. Excecoes nao tratadas podem deixar conexoes abertas.
- **Fix:** Garantir `try/finally` com `session.close()` em todas as ocorrencias

### M-06: Alembic como dependencia sem uso
- **Arquivo:** `pyproject.toml:13`
- **Descricao:** `alembic>=1.14` esta listado como dependencia, mas o projeto usa scripts standalone para migracoes. `CLAUDE.md` confirma: "No Alembic".
- **Fix:** Remover do `pyproject.toml` ou adotar Alembic de fato

### M-07: as any em componentes recharts
- **Arquivos:** `frontend/src/app/dashboard/admin/metrics/page.tsx:263,271`, `frontend/src/app/dashboard/metrics/usage-tab.tsx:173,180`
- **Descricao:** Type casts `as any` para contornar tipos do recharts. Perde type safety.
- **Fix:** Instalar `@types/recharts` ou definir tipos adequados para os formatters

### M-08: catch (e: any) em vez de catch (e: unknown)
- **Arquivos:** `frontend/src/app/dashboard/docs/[repoName]/page.tsx:145,158,196`, `frontend/src/app/dashboard/rules/page.tsx:144,157,168,179`
- **Descricao:** TypeScript best practice e usar `catch (e: unknown)` com type guard, nao `catch (e: any)`.
- **Fix:** Trocar para `catch (e: unknown)` e usar `instanceof Error`

### M-09: .env.example incompleto
- **Arquivo:** `.env.example`
- **Descricao:** Faltam variaveis documentadas no CLAUDE.md: `NEXT_PUBLIC_API_URL`, `APP_URL`, `SMTP_*`, `CORS_ORIGINS`. Dificulta onboarding de novos devs.
- **Fix:** Adicionar todas as variaveis com descricoes

### M-10: .gitignore incompleto
- **Arquivo:** `.gitignore`
- **Descricao:** Faltam entradas para `.env.*.local`, `*.pem`, `*.key`, `credentials.json`, `agent/config.yaml`.
- **Fix:** Adicionar os patterns ausentes

### M-11: Inconsistencia raw SQL vs ORM
- **Arquivos:** Quase todas as rotas usam `text()` com SQL raw, exceto `users.py` que usa `db.query(User).filter()`. Modelos SQLAlchemy estao definidos mas subutilizados.
- **Descricao:** O projeto tem modelos ORM completos mas ~95% das queries sao raw SQL. Isso anula beneficios do ORM (type safety, relacoes, validacao).
- **Fix:** Nao e urgente, mas ao refatorar rotas, migrar gradualmente para ORM

### M-12: Promise.allSettled sem inspecao de status
- **Arquivo:** `frontend/src/app/dashboard/metrics/security-tab.tsx:73-76`
- **Descricao:** `Promise.allSettled()` chamado mas o status individual de cada promise nao e verificado. Se uma falhar, o usuario nao sabe qual.
- **Fix:** Inspecionar `.status === "rejected"` e mostrar feedback

### M-13: Polling do sidebar sem visibilitychange
- **Arquivo:** `frontend/src/components/layout/dashboard-sidebar.tsx:57-62`
- **Descricao:** setInterval de 30s para incidents stats roda mesmo quando a aba esta em background.
- **Fix:** Usar `document.visibilityState` ou `requestIdleCallback` para pausar quando inativo

### M-14: Scripts de migracao sem transacao em alguns casos
- **Arquivos:** Scripts mais antigos (`migrate_add_orgs.py`, `migrate_add_password_hash.py`) usam `psycopg2` com `autocommit=True`, enquanto os mais novos usam `engine.begin()` com rollback automatico.
- **Fix:** Padronizar todos para `engine.begin()`

---

## 4. Problemas Baixos

### B-01: Helpers wrapper desnecessarios
- **Arquivos:** `admin.py:19`, `monitor.py:18`, `reviews.py:22`, `knowledge.py:29`
- **Descricao:** Funcoes como `_get_admin_user()` que apenas retornam o resultado de `require_role()`. Nao adicionam logica.
- **Fix:** Usar `require_role()` direto na assinatura da rota

### B-02: Import duplicado em main.py
- **Arquivo:** `app/main.py:5,7`
- **Descricao:** `from fastapi import Depends` importado separadamente quando ja poderia estar na linha 3.
- **Fix:** Consolidar imports

### B-03: conftest._mock_session() e funcao, nao fixture
- **Arquivo:** `tests/conftest.py`
- **Descricao:** `_mock_session()` e uma funcao helper, nao uma fixture pytest. Pode causar confusao sobre quando usar.
- **Fix:** Manter como funcao mas documentar claramente, ou converter em fixture

### B-04: Testes com cleanup manual em vez de fixture
- **Arquivos:** `test_executive.py`, `test_docs.py`
- **Descricao:** Alguns testes fazem `app.dependency_overrides.clear()` manualmente sem `try/finally`, podendo vazar estado se o teste falhar antes do cleanup.
- **Fix:** Usar fixture com `yield` para cleanup automatico

### B-05: setTimeout de confetti sem cleanup
- **Arquivo:** `frontend/src/app/dashboard/docs/[repoName]/page.tsx:194`
- **Descricao:** `setTimeout(() => setShowConfetti(false), 5000)` nao armazenado em ref.
- **Fix:** Armazenar em ref e limpar no unmount

### B-06: README.md desatualizado
- **Arquivo:** `README.md:9`
- **Descricao:** Menciona "Claude API (Haiku para consultas, Sonnet para analises)" mas o sistema agora usa multi-provider via DB.
- **Fix:** Atualizar para refletir o sistema atual de provedores

---

## O Que Esta Bem

1. **Cobertura de testes solida** — 299+ testes cobrindo todas as rotas principais, roles, e edge cases
2. **Multi-tenancy consistente nas rotas** — Quase todas as queries filtram por `org_id` corretamente
3. **Sistema de roles bem implementado** — `require_role()` como dependency injection e robusto
4. **Separacao frontend/backend clara** — API REST bem definida, frontend independente
5. **Streaming SSE funcional** — Chat com streaming e fallback bem implementados
6. **Sistema de criptografia de API keys** — Fernet com encrypt/decrypt/mask e solido (apesar dos issues de config)
7. **Tratamento de erros em portugues** — Mensagens de erro consistentes em PT-BR nas rotas
8. **PDF export centralizado** — PDFGenerator com template consistente para 5 tipos de relatorio
9. **Onboarding wizard completo** — Fluxo de setup com 5 etapas e redirect logic
10. **Health check administrativo** — Verificacao paralela de 7 componentes do sistema

---

## Plano de Acao

### Fase 1 — Imediato (antes de qualquer deploy)
| # | Acao | Arquivos | Esforco |
|---|------|----------|---------|
| 1 | Remover chave de criptografia do log | `encryption.py` | 5 min |
| 2 | Mover CORS origins para env var | `main.py`, `config.py` | 15 min |
| 3 | Substituir localStorage direto por getAccessToken() | `impact/page.tsx` | 5 min |
| 4 | Tornar org_id obrigatorio em _clear_repo_chunks | `ingestor.py` | 10 min |
| 5 | Falhar se LLM_ENCRYPTION_KEY nao configurada | `encryption.py` | 10 min |

### Fase 2 — Esta semana
| # | Acao | Arquivos | Esforco |
|---|------|----------|---------|
| 6 | Criar helper build_update_query com whitelist | `monitor.py`, `llm_providers.py`, `incidents.py`, `rules.py`, `impact.py` | 1h |
| 7 | Adicionar cleanup em todos os setInterval/setTimeout | 6 arquivos frontend | 30 min |
| 8 | Adicionar toast.error nos catch blocks criticos | 15+ arquivos frontend | 45 min |
| 9 | Extrair _fake_user() para conftest.py | 10+ arquivos de teste | 30 min |
| 10 | Adicionar health checks ao docker-compose.yml | `docker-compose.yml` | 15 min |

### Fase 3 — Proximo sprint
| # | Acao | Arquivos | Esforco |
|---|------|----------|---------|
| 11 | Pinagem de dependencias com upper bound | `pyproject.toml` | 20 min |
| 12 | Separar Docker dev/prod | `Dockerfile.api`, `frontend/Dockerfile`, `docker-compose.yml` | 1h |
| 13 | Completar .env.example | `.env.example` | 15 min |
| 14 | Adicionar TTL ao cache JWKS | `auth.py` | 30 min |
| 15 | Padronizar scripts de migracao | `scripts/` | 1h |
| 16 | Remover alembic do pyproject.toml | `pyproject.toml` | 5 min |
| 17 | Atualizar README.md | `README.md` | 20 min |

### Fase 4 — Ongoing
| # | Acao | Arquivos | Esforco |
|---|------|----------|---------|
| 18 | Migrar gradualmente de raw SQL para ORM | Todas as rotas | Continuo |
| 19 | Adicionar fixture com yield para cleanup de testes | Todos os testes | 1h |
| 20 | Implementar visibilitychange para polling | Sidebar, security-tab | 30 min |

---

*Relatorio gerado por auditoria automatizada em 2026-03-07. Total: 57 issues identificados (4 criticos, 18 altos, 26 medios, 9 baixos).*
