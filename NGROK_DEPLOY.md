# Deploy — Frontend Vercel + Backend Local via ngrok

## Setup inicial (uma unica vez)

### 1. Configurar ngrok com dominio estatico

No painel ngrok.com:
- Va em Cloud Edge > Domains
- Crie um dominio estatico gratuito
  Ex: `memora-rafael.ngrok-free.app`
- Sempre use este dominio — URL nunca muda

### 2. Gerar LLM_ENCRYPTION_KEY

```powershell
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Copie o resultado para `LLM_ENCRYPTION_KEY` no `.env`

### 3. Preencher o .env

Copie `.env.example` para `.env` e preencha:

| Variavel | Onde obter |
|---|---|
| `DATABASE_URL` | Supabase Dashboard > Settings > Database > Connection string |
| `OPENAI_API_KEY` | https://platform.openai.com/api-keys |
| `SUPABASE_URL` | Supabase Dashboard > Settings > API > Project URL |
| `SUPABASE_SERVICE_ROLE_KEY` | Supabase Dashboard > Settings > API > service_role |
| `SUPABASE_JWT_SECRET` | Supabase Dashboard > Settings > API > JWT Secret |
| `LLM_ENCRYPTION_KEY` | Gerada no passo anterior |
| `CORS_ORIGINS` | Deixar em branco (start.ps1 preenche automaticamente) |

### 4. Rodar migrations

```powershell
python scripts/run_all_migrations.py
```

### 5. Deploy do frontend na Vercel

1. [vercel.com](https://vercel.com) > New Project > importar repositorio
2. Root Directory: `frontend`
3. Framework: Next.js
4. Environment Variables:
   - `NEXT_PUBLIC_SUPABASE_URL`
   - `NEXT_PUBLIC_SUPABASE_ANON_KEY`
   - `NEXT_PUBLIC_API_URL` = `https://SEU-DOMINIO.ngrok-free.app`
5. Deploy > copiar URL gerada

## Uso diario

```powershell
# Terminal 1 — ngrok (deixar aberto)
ngrok http --domain=attentive-taylor-snoopy.ngrok-free.dev 8000

# Terminal 2 — backend
.\start.ps1 https://SEU-DOMINIO.ngrok-free.app
```

Abrir: `https://SEU-PROJETO.vercel.app`

## Checklist antes de compartilhar

### Backend
- [ ] ngrok rodando com dominio estatico
- [ ] `.\start.ps1` executado sem erros
- [ ] http://localhost:8000/api/health retorna 200
- [ ] https://SEU-DOMINIO.ngrok-free.app/api/health retorna 200

### Vercel
- [ ] `NEXT_PUBLIC_API_URL` = URL do ngrok estatico
- [ ] Ultimo deploy bem-sucedido
- [ ] Tela de login aparece ao abrir a URL
- [ ] Login com admin funciona
- [ ] Primeira pergunta no assistente retorna resposta
