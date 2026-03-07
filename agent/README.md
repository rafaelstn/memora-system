# Memora Agent

Agente de monitoramento de logs que roda no servidor do cliente. Lê arquivos de log em tempo real e envia automaticamente para o Memora.

## Requisitos

- Python 3.9+
- `pip install pyyaml requests`

## Instalação rápida

### Linux (systemd)

```bash
sudo bash install.sh
```

O script interativo vai perguntar:
1. URL do Memora
2. Token do projeto (gerado no painel)
3. Caminho do arquivo de log

### Windows (Task Scheduler)

```powershell
powershell -ExecutionPolicy Bypass -File install.ps1
```

### Manual

```bash
cp config.yaml.example config.yaml
# Edite config.yaml com seu token e caminhos
python memora_agent.py --config config.yaml
```

## Configuração

Edite `config.yaml`:

```yaml
memora_url: https://seu-memora.com
project_token: seu-token-aqui

sources:
  - type: file
    path: /var/log/myapp/error.log
    format: auto  # auto | json | python | loguru | nginx | plain

filters:
  min_level: warning  # ignora debug e info

batch_size: 100
flush_interval: 5
```

## Formatos suportados

O agente detecta automaticamente:

- **Python logging**: `2026-03-06 10:30:00 - module - ERROR - message`
- **Loguru**: `2026-03-06 10:30:00.123 | ERROR | module:func:42 - message`
- **JSON**: `{"level": "error", "message": "...", "timestamp": "..."}`
- **Nginx**: `2026/03/06 10:30:00 [error] 1234#0: message`
- **Plain text**: Detecta nível por palavras-chave (ERROR, CRITICAL, etc)

## Comandos úteis

```bash
# Status (Linux)
systemctl status memora-agent

# Logs do agente
journalctl -u memora-agent -f

# Parar
systemctl stop memora-agent

# Reiniciar
systemctl restart memora-agent
```

## Como funciona

1. Faz tail nos arquivos configurados (acompanha em tempo real)
2. Mantém posição lida em `.memora_state.json` — não reenvia logs após restart
3. Filtra pelo nível mínimo configurado
4. Agrupa em batch e envia para `POST /api/logs/ingest`
5. Retry com backoff exponencial se o Memora estiver offline
