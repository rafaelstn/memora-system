# ============================================================
# MEMORA - STOP (encerra backend, ngrok e processos orphans)
# ============================================================

Write-Host ""
Write-Host "================================================" -ForegroundColor Cyan
Write-Host "  MEMORA - Encerrando servicos" -ForegroundColor Cyan
Write-Host "================================================" -ForegroundColor Cyan
Write-Host ""

$stopped = 0

# --- 1. Encerrar uvicorn (python) na porta 8000 ---------------
$pids8000 = netstat -ano | Select-String ":8000\s.*LISTENING" | ForEach-Object {
    ($_ -split "\s+")[-1]
} | Sort-Object -Unique

if ($pids8000) {
    foreach ($pid in $pids8000) {
        try {
            $proc = Get-Process -Id $pid -ErrorAction Stop
            Write-Host "  Encerrando $($proc.ProcessName) (PID $pid) na porta 8000..." -ForegroundColor Yellow
            Stop-Process -Id $pid -Force -ErrorAction Stop
            $stopped++
        } catch {}
    }
    Write-Host "  Backend encerrado" -ForegroundColor Green
} else {
    Write-Host "  Backend nao estava rodando" -ForegroundColor Gray
}

# --- 2. Encerrar ngrok -----------------------------------------
$ngrokProcs = Get-Process -Name "ngrok" -ErrorAction SilentlyContinue
if ($ngrokProcs) {
    foreach ($proc in $ngrokProcs) {
        Write-Host "  Encerrando ngrok (PID $($proc.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        $stopped++
    }
    Write-Host "  ngrok encerrado" -ForegroundColor Green
} else {
    Write-Host "  ngrok nao estava rodando" -ForegroundColor Gray
}

# --- 3. Encerrar janelas PowerShell do backend (MEMORA BACKEND) -
$psProcs = Get-Process -Name "powershell", "pwsh" -ErrorAction SilentlyContinue | Where-Object {
    $_.MainWindowTitle -match "MEMORA"
}
if ($psProcs) {
    foreach ($proc in $psProcs) {
        Write-Host "  Encerrando janela PowerShell (PID $($proc.Id))..." -ForegroundColor Yellow
        Stop-Process -Id $proc.Id -Force -ErrorAction SilentlyContinue
        $stopped++
    }
}

# --- Resumo ----------------------------------------------------
Write-Host ""
Write-Host "================================================" -ForegroundColor Green
Write-Host "  MEMORA ENCERRADO" -ForegroundColor Green
Write-Host "================================================" -ForegroundColor Green
Write-Host ""
if ($stopped -eq 0) {
    Write-Host "  Nenhum servico estava rodando" -ForegroundColor Gray
} else {
    Write-Host "  $stopped processo(s) encerrado(s)" -ForegroundColor White
}
Write-Host "  Para subir novamente: .\start.ps1" -ForegroundColor White
Write-Host ""
