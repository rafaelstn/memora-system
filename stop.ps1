$ErrorActionPreference = "Stop"

# --- Funcoes auxiliares ------------------------------------------------------
function Write-Info  { param([string]$Msg) Write-Host "[INFO]  $Msg" -ForegroundColor Cyan }
function Write-Ok    { param([string]$Msg) Write-Host "[OK]    $Msg" -ForegroundColor Green }
function Write-Warn  { param([string]$Msg) Write-Host "[WARN]  $Msg" -ForegroundColor Yellow }
function Write-Fail  { param([string]$Msg) Write-Host "[ERRO]  $Msg" -ForegroundColor Red; exit 1 }

$RootDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $RootDir

# --- docker-compose command --------------------------------------------------
$dcCmd = $null
try {
    $null = docker compose version 2>$null
    if ($LASTEXITCODE -eq 0) { $dcCmd = "docker compose" }
} catch {}
if (-not $dcCmd) {
    try {
        $null = docker-compose version 2>$null
        if ($LASTEXITCODE -eq 0) { $dcCmd = "docker-compose" }
    } catch {}
}
if (-not $dcCmd) {
    Write-Fail "docker-compose nao encontrado."
}

# --- 1. Verificar containers ------------------------------------------------
$running = 0
try {
    $containers = Invoke-Expression "$dcCmd ps --format '{{.Name}}'" 2>$null
    if ($containers) {
        $running = ($containers | Select-String "memora" | Measure-Object).Count
    }
} catch {}

if ($running -eq 0) {
    Write-Host ""
    Write-Info "Nenhum servico Memora rodando."
    Write-Host ""
    exit 0
}

Write-Info "$running servico(s) Memora rodando"
Write-Host ""

# --- 2. Encerrar servicos ---------------------------------------------------
foreach ($service in @("memora-web", "memora-api")) {
    try {
        $running_containers = docker ps --format '{{.Names}}' 2>$null
        if ($running_containers -and ($running_containers | Select-String $service)) {
            Write-Info "Encerrando $service..."
            docker stop $service 2>$null | Out-Null
        }
    } catch {}
}

Write-Info "Removendo containers..."
try {
    Invoke-Expression "$dcCmd down"
} catch {
    Write-Warn "Erro ao remover containers: $_"
}

Write-Host ""

# --- 3. Painel final --------------------------------------------------------
Write-Host "  ================================================" -ForegroundColor Green
Write-Host "  |         MEMORA -- ENCERRADO                   |" -ForegroundColor Green
Write-Host "  ================================================" -ForegroundColor Green
Write-Host "  |  Todos os servicos encerrados                 |" -ForegroundColor Green
Write-Host "  |  Banco Supabase: sem alteracao (remoto)       |" -ForegroundColor Green
Write-Host "  ================================================" -ForegroundColor Green
Write-Host "  |  Para subir novamente: .\start.ps1            |" -ForegroundColor Green
Write-Host "  ================================================" -ForegroundColor Green
Write-Host ""
