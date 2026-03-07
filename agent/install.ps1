# Memora Agent — Instalacao Windows (Task Scheduler)
# Execute como Administrador: powershell -ExecutionPolicy Bypass -File install.ps1

$ErrorActionPreference = "Stop"

$InstallDir = "C:\memora-agent"
$TaskName = "MemoraAgent"

Write-Host "=== Memora Agent — Instalacao ===" -ForegroundColor Cyan
Write-Host ""

# Check Python
try {
    $pyVersion = & python --version 2>&1
    Write-Host "Python encontrado: $pyVersion"
} catch {
    Write-Host "Python nao encontrado. Instale em python.org" -ForegroundColor Red
    exit 1
}

# Install dependencies
Write-Host "Instalando dependencias..."
& pip install pyyaml requests

# Create install dir
if (-not (Test-Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir | Out-Null
}
Copy-Item "memora_agent.py" "$InstallDir\" -Force

# Config
$ConfigPath = "$InstallDir\config.yaml"
if (-not (Test-Path $ConfigPath)) {
    $MemoraUrl = Read-Host "URL do Memora (ex: https://seu-memora.com)"
    $Token = Read-Host "Token do projeto"
    $LogPath = Read-Host "Caminho do arquivo de log a monitorar"

    @"
memora_url: $MemoraUrl
project_token: $Token
sources:
  - type: file
    path: $LogPath
    format: auto
filters:
  min_level: warning
batch_size: 100
flush_interval: 5
"@ | Out-File -FilePath $ConfigPath -Encoding utf8

    Write-Host "Config salvo em $ConfigPath" -ForegroundColor Green
} else {
    Write-Host "Config existente mantido: $ConfigPath"
}

# Create scheduled task (runs at startup, restarts on failure)
$Action = New-ScheduledTaskAction `
    -Execute "python" `
    -Argument "$InstallDir\memora_agent.py --config $ConfigPath --log-file $InstallDir\memora-agent.log" `
    -WorkingDirectory $InstallDir

$Trigger = New-ScheduledTaskTrigger -AtStartup
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -RestartCount 999 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -ExecutionTimeLimit (New-TimeSpan -Days 365)

$Principal = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest

# Remove old task if exists
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

Register-ScheduledTask `
    -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Settings $Settings `
    -Principal $Principal `
    -Description "Memora Agent - Monitor de Logs"

# Start the task
Start-ScheduledTask -TaskName $TaskName

Write-Host ""
Write-Host "=== Instalacao concluida! ===" -ForegroundColor Green
Write-Host "Status: Get-ScheduledTask -TaskName $TaskName"
Write-Host "Logs:   $InstallDir\memora-agent.log"
Write-Host "Config: $ConfigPath"
Write-Host ""
Get-ScheduledTask -TaskName $TaskName | Format-List TaskName, State
