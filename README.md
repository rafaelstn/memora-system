# Memora

Inteligência Técnica Operacional para PMEs brasileiras. Transforma o codebase da empresa em um assistente de suporte que responde perguntas sobre o sistema em português, com base no código real.

## Stack

- **Python 3.11+** com FastAPI
- **PostgreSQL** (Supabase) com pgvector para busca vetorial
- **Claude API** (Haiku para consultas, Sonnet para análises)
- **OpenAI text-embedding-3-small** para embeddings
- **AST chunking** para indexação inteligente de código Python
- **Busca híbrida**: semântica (pgvector) + BM25

## Setup local

### 1. Clonar e instalar dependências

```bash
git clone <repo-url>
cd Memora-system
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### 2. Configurar variáveis de ambiente

```bash
cp .env.example .env
# Editar .env com suas chaves:
# - DATABASE_URL (Supabase)
# - OPENAI_API_KEY
# - ANTHROPIC_API_KEY
```

### 3. Verificar conexão com o banco

```bash
python scripts/check_connection.py
```

### 4. Criar tabelas

```bash
python scripts/setup_db.py
```

### 5. Indexar um repositório

```bash
# Repositório local
python scripts/index_repo.py /caminho/do/repo nome-do-repo

# Exemplo: indexar o próprio Memora
python scripts/index_repo.py . memora
```

### 6. Rodar a API

```bash
uvicorn app.main:app --reload
```

Acesse:
- **Chat**: http://localhost:8000
- **API docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/api/health

### 7. Testar fluxo completo

```bash
python scripts/test_flow.py
```

## Endpoints

| Método | Rota | Descrição |
|--------|------|-----------|
| POST | `/api/ask` | Faz uma pergunta sobre o codebase |
| POST | `/api/ingest` | Indexa um repositório |
| POST | `/api/webhooks/github` | Recebe push events do GitHub |
| GET | `/api/health` | Status da API e banco |

## Testes

```bash
pytest
```

## Estrutura

```
app/
├── main.py              # FastAPI app
├── config.py            # Settings
├── api/routes/          # Endpoints HTTP
├── core/                # Lógica de negócio
│   ├── chunker.py       # AST chunking
│   ├── embedder.py      # OpenAI embeddings
│   ├── search.py        # Busca híbrida
│   ├── assistant.py     # Orquestração de respostas
│   └── ingestor.py      # Pipeline de ingestão
├── integrations/        # Clients externos
│   ├── llm_client.py    # Claude API
│   └── github_client.py # Git operations
├── models/              # SQLAlchemy models
└── db/                  # Database config
scripts/                 # Utilitários CLI
web/                     # Interface de chat
tests/                   # Testes automatizados
```
