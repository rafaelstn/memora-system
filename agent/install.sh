#!/bin/bash
# Memora Agent — Instalacao Linux (systemd)
set -e

INSTALL_DIR="/opt/memora-agent"
SERVICE_NAME="memora-agent"

echo "=== Memora Agent — Instalacao ==="
echo ""

# Check root
if [ "$EUID" -ne 0 ]; then
  echo "Execute como root: sudo bash install.sh"
  exit 1
fi

# Check Python
if ! command -v python3 &> /dev/null; then
  echo "Python 3 nao encontrado. Instale com: apt install python3"
  exit 1
fi

# Check pip dependencies
python3 -c "import yaml, requests" 2>/dev/null || {
  echo "Instalando dependencias..."
  pip3 install pyyaml requests
}

# Create install dir
mkdir -p "$INSTALL_DIR"
cp memora_agent.py "$INSTALL_DIR/"

# Config
if [ ! -f "$INSTALL_DIR/config.yaml" ]; then
  echo ""
  read -p "URL do Memora (ex: https://seu-memora.com): " MEMORA_URL
  read -p "Token do projeto: " PROJECT_TOKEN
  read -p "Caminho do arquivo de log a monitorar: " LOG_PATH

  cat > "$INSTALL_DIR/config.yaml" <<EOF
memora_url: $MEMORA_URL
project_token: $PROJECT_TOKEN
sources:
  - type: file
    path: $LOG_PATH
    format: auto
filters:
  min_level: warning
batch_size: 100
flush_interval: 5
EOF
  echo "Config salvo em $INSTALL_DIR/config.yaml"
else
  echo "Config existente mantido: $INSTALL_DIR/config.yaml"
fi

# Create systemd service
cat > /etc/systemd/system/${SERVICE_NAME}.service <<EOF
[Unit]
Description=Memora Agent — Monitor de Logs
After=network.target

[Service]
Type=simple
WorkingDirectory=$INSTALL_DIR
ExecStart=/usr/bin/python3 $INSTALL_DIR/memora_agent.py --config $INSTALL_DIR/config.yaml --log-file /var/log/memora-agent.log
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# Enable and start
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl start "$SERVICE_NAME"

echo ""
echo "=== Instalacao concluida! ==="
echo "Status: systemctl status $SERVICE_NAME"
echo "Logs:   journalctl -u $SERVICE_NAME -f"
echo "Config: $INSTALL_DIR/config.yaml"
echo ""
systemctl status "$SERVICE_NAME" --no-pager
