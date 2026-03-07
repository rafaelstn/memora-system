param(
    [string]$NgrokDomain = "attentive-taylor-snoopy.ngrok-free.dev"
)

# ============================================================
# MEMORA - START COMPLETO
# ============================================================

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  MEMORA - Iniciando sistema completo" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

# ------------------------------------------------------------
# PASSO 1 - Verifica .env
# ------------------------------------------------------------
Write-Host "[1/4] Verificando configuracao..." -ForegroundColor Yellow

if (-not (Test-Path ".env")) {
    Write-Host "ERRO: .env nao encontrado." -ForegroundColor Red
    Write-Host "      Copie .env.example para .env e preencha as variaveis." -ForegroundColor Red
    exit 1
}

# Le variaveis do .env
$envVars = @{}
Get-Content ".env" | ForEach-Object {
    if ($_ -match "^([^#][^=]*)=(.*)$") {
        $envVars[$matches[1].Trim()] = $matches[2].Trim()
    }
}

# Verifica variaveis obrigatorias
$required = @("DATABASE_URL", "OPENAI_API_KEY", "SUPABASE_URL", "SUPABASE_SERVICE_ROLE_KEY", "SUPABASE_JWT_SECRET", "LLM_ENCRYPTION_KEY")
$missing = @()
foreach ($var in $required) {
    if (-not $envVars[$var] -or $envVars[$var] -eq "") {
        $missing += $var
    }
}

if ($missing.Count -gt 0) {
    Write-Host "ERRO: Variaveis obrigatorias nao preenchidas no .env:" -ForegroundColor Red
    $missing | ForEach-Object { Write-Host "      - $_" -ForegroundColor Red }
    exit 1
}

Write-Host "  .env OK - variaveis obrigatorias presentes" -ForegroundColor Green

# ------------------------------------------------------------
# PASSO 2 - Migrations
# ------------------------------------------------------------
Write-Host ""
Write-Host "[2/4] Rodando migrations..." -ForegroundColor Yellow

$migrationResult = python scripts/run_all_migrations.py 2>&1
$migrationOutput = $migrationResult | Out-String

if ($LASTEXITCODE -ne 0) {
    Write-Host "ERRO nas migrations:" -ForegroundColor Red
    Write-Host $migrationOutput -ForegroundColor Red
    exit 1
}

# Mostra resultado resumido
$migrationResult | ForEach-Object {
    if ($_ -match "\[OK\]") {
        Write-Host "  $_" -ForegroundColor Green
    } elseif ($_ -match "\[SKIP\]") {
        Write-Host "  $_" -ForegroundColor Gray
    } elseif ($_ -match "\[ERRO\]") {
        Write-Host "  $_" -ForegroundColor Red
    }
}

Write-Host "  Migrations concluidas" -ForegroundColor Green

# ------------------------------------------------------------
# PASSO 3 - ngrok
# ------------------------------------------------------------
Write-Host ""
Write-Host "[3/4] Iniciando ngrok..." -ForegroundColor Yellow

# Verifica se ngrok esta instalado
if (-not (Get-Command ngrok -ErrorAction SilentlyContinue)) {
    Write-Host "ERRO: ngrok nao encontrado." -ForegroundColor Red
    Write-Host "      Instale em: https://ngrok.com/download" -ForegroundColor Red
    exit 1
}

# Define dominio
if ($NgrokDomain -eq "") {
    # Tenta ler dominio salvo
    $savedDomain = ""
    if (Test-Path ".ngrok-domain") {
        $savedDomain = Get-Content ".ngrok-domain" -Raw
        $savedDomain = $savedDomain.Trim()
    }

    if ($savedDomain -ne "") {
        Write-Host "  Usando dominio salvo: $savedDomain" -ForegroundColor Green
        $NgrokDomain = $savedDomain
    } else {
        Write-Host ""
        Write-Host "  Nenhum dominio ngrok configurado." -ForegroundColor Yellow
        Write-Host "  Opcoes:" -ForegroundColor White
        Write-Host '    A) Dominio estatico (recomendado - URL fixa):' -ForegroundColor White
        Write-Host '       1. Acesse ngrok.com, va em Cloud Edge, Domains, New Domain' -ForegroundColor White
        Write-Host '       2. Execute: .\start.ps1 -NgrokDomain seu-dominio.ngrok-free.app' -ForegroundColor White
        Write-Host ""
        Write-Host '    B) URL temporaria (muda a cada vez):' -ForegroundColor White
        $useTemp = Read-Host "  Usar URL temporaria agora? (s/n)"
        if ($useTemp -ne "s") {
            Write-Host "Configure um dominio estatico e tente novamente." -ForegroundColor Yellow
            exit 0
        }
        $NgrokDomain = ""
    }
}

# Salva dominio para proximas execucoes
if ($NgrokDomain -ne "") {
    $NgrokDomain | Set-Content ".ngrok-domain"
    Write-Host "  Dominio salvo para proximas execucoes" -ForegroundColor Gray
}

# Inicia ngrok em background
if ($NgrokDomain -ne "") {
    Start-Process -FilePath "ngrok" -ArgumentList "http", "--domain=$NgrokDomain", "8000" -WindowStyle Hidden
    $NgrokUrl = "https://$NgrokDomain"
} else {
    Start-Process -FilePath "ngrok" -ArgumentList "http", "8000" -WindowStyle Hidden
    # Aguarda ngrok iniciar e pega URL via API local
    Start-Sleep -Seconds 3
    try {
        $ngrokApi = Invoke-RestMethod -Uri "http://localhost:4040/api/tunnels" -ErrorAction Stop
        $NgrokUrl = $ngrokApi.tunnels[0].public_url
    } catch {
        Write-Host "AVISO: Nao foi possivel obter URL do ngrok automaticamente." -ForegroundColor Yellow
        Write-Host "       Verifique em http://localhost:4040" -ForegroundColor Yellow
        $NgrokUrl = "URL_PENDENTE"
    }
}

Write-Host "  ngrok iniciado: $NgrokUrl" -ForegroundColor Green

# Atualiza CORS no .env
$envContent = Get-Content ".env" -Raw

if ($envContent -match "CORS_ORIGINS=") {
    $envContent = $envContent -replace "CORS_ORIGINS=.*", "CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,$NgrokUrl"
} else {
    $envContent += "`nCORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000,$NgrokUrl"
}

if ($envContent -match "APP_URL=") {
    $envContent = $envContent -replace "APP_URL=.*", "APP_URL=$NgrokUrl"
} else {
    $envContent += "`nAPP_URL=$NgrokUrl"
}

$envContent | Set-Content ".env"
Write-Host "  CORS atualizado no .env" -ForegroundColor Gray

# ------------------------------------------------------------
# PASSO 4 - Backend
# ------------------------------------------------------------
Write-Host ""
Write-Host "[4/4] Iniciando backend..." -ForegroundColor Yellow

Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd '$PWD'; Write-Host 'MEMORA BACKEND' -ForegroundColor Cyan; python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload"

# Aguarda backend responder
$attempts = 0
$ready = $false
do {
    Start-Sleep -Seconds 2
    $attempts++
    try {
        Invoke-WebRequest -Uri "http://localhost:8000/api/health" -TimeoutSec 5 -UseBasicParsing -ErrorAction Stop | Out-Null
        $ready = $true
    } catch {}
} while (-not $ready -and $attempts -lt 20)

if (-not $ready) {
    Write-Host "ERRO: Backend nao respondeu em 40 segundos." -ForegroundColor Red
    Write-Host "      Verifique a janela do backend para detalhes." -ForegroundColor Red
    exit 1
}

Write-Host "  Backend rodando em http://localhost:8000" -ForegroundColor Green

Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  MEMORA RODANDO" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Backend local:   http://localhost:8000" -ForegroundColor White
Write-Host "  Backend publico: $NgrokUrl" -ForegroundColor White
Write-Host "  Health check:    http://localhost:8000/api/health" -ForegroundColor White
Write-Host ""
Write-Host "  VERCEL - Confirme que esta variavel esta configurada:" -ForegroundColor Yellow
Write-Host "  NEXT_PUBLIC_API_URL = $NgrokUrl" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Se mudou a URL do ngrok:" -ForegroundColor Yellow
Write-Host '  vercel.com, projeto, Settings, Environment Variables' -ForegroundColor White
Write-Host "  Atualizar NEXT_PUBLIC_API_URL e fazer Redeploy" -ForegroundColor White
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
