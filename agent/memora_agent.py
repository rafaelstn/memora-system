#!/usr/bin/env python3
"""
Memora Agent — Monitora arquivos de log e envia para o Memora automaticamente.

Instalacao:
  pip install pyyaml requests

Uso:
  python memora_agent.py --config config.yaml
"""
import argparse
import json
import logging
import os
import re
import signal
import sys
import time
from datetime import datetime
from pathlib import Path

import requests
import yaml

# --- Config ---

DEFAULT_CONFIG = {
    "memora_url": "http://localhost:8000",
    "project_token": "",
    "sources": [],
    "filters": {"min_level": "warning"},
    "batch_size": 100,
    "flush_interval": 5,
}

LEVEL_PRIORITY = {"debug": 0, "info": 1, "warning": 2, "error": 3, "critical": 4}

STATE_FILE = ".memora_state.json"

logger = logging.getLogger("memora-agent")


def load_config(path: str) -> dict:
    with open(path) as f:
        user_config = yaml.safe_load(f) or {}
    config = {**DEFAULT_CONFIG, **user_config}
    if not config["project_token"]:
        logger.error("project_token nao configurado em %s", path)
        sys.exit(1)
    return config


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


# --- Log parsing ---

# Python logging format: 2026-03-06 10:30:00,123 - module - ERROR - message
PYTHON_LOG_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}[,.]?\d*)\s*[-–]\s*(\S+)\s*[-–]\s*(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*[-–]\s*(.+)",
    re.IGNORECASE,
)

# Loguru format: 2026-03-06 10:30:00.123 | ERROR | module:func:42 - message
LOGURU_RE = re.compile(
    r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\s*\|\s*(DEBUG|INFO|WARNING|ERROR|CRITICAL)\s*\|\s*(\S+)\s*[-–]\s*(.+)",
    re.IGNORECASE,
)

# JSON log: {"level": "error", "message": "...", ...}
JSON_LOG_RE = re.compile(r"^\s*\{.+\}\s*$")

# Nginx error: 2026/03/06 10:30:00 [error] 1234#0: *5 message
NGINX_RE = re.compile(
    r"^(\d{4}/\d{2}/\d{2}\s+\d{2}:\d{2}:\d{2})\s+\[(\w+)\]\s+(.+)",
)

# Generic level detection
LEVEL_KEYWORDS = {
    "critical": ["CRITICAL", "FATAL"],
    "error": ["ERROR", "ERR"],
    "warning": ["WARNING", "WARN"],
    "info": ["INFO"],
    "debug": ["DEBUG", "TRACE"],
}


def detect_level_from_text(text: str) -> str:
    upper = text.upper()
    for level, keywords in LEVEL_KEYWORDS.items():
        for kw in keywords:
            if kw in upper:
                return level
    return "info"


def parse_line(line: str, fmt: str = "auto") -> dict | None:
    """Parse a log line into a structured dict. Returns None if unparseable."""
    line = line.strip()
    if not line:
        return None

    # Try JSON first
    if fmt in ("auto", "json") and JSON_LOG_RE.match(line):
        try:
            data = json.loads(line)
            return {
                "level": data.get("level", data.get("levelname", "info")).lower(),
                "message": data.get("message", data.get("msg", line)),
                "source": data.get("source", data.get("module", data.get("logger"))),
                "stack_trace": data.get("stack_trace", data.get("traceback", data.get("exception"))),
                "occurred_at": data.get("timestamp", data.get("time", data.get("@timestamp"))),
                "metadata": {k: v for k, v in data.items() if k not in ("level", "levelname", "message", "msg", "source", "module", "stack_trace", "traceback", "exception", "timestamp", "time", "@timestamp", "logger")},
            }
        except json.JSONDecodeError:
            pass

    # Python logging
    if fmt in ("auto", "python"):
        m = PYTHON_LOG_RE.match(line)
        if m:
            return {
                "level": m.group(3).lower(),
                "message": m.group(4),
                "source": m.group(2),
                "stack_trace": None,
                "occurred_at": m.group(1),
                "metadata": None,
            }

    # Loguru
    if fmt in ("auto", "loguru"):
        m = LOGURU_RE.match(line)
        if m:
            return {
                "level": m.group(2).lower(),
                "message": m.group(4),
                "source": m.group(3),
                "stack_trace": None,
                "occurred_at": m.group(1),
                "metadata": None,
            }

    # Nginx
    if fmt in ("auto", "nginx"):
        m = NGINX_RE.match(line)
        if m:
            level = m.group(2).lower()
            if level == "emerg":
                level = "critical"
            elif level == "crit":
                level = "critical"
            elif level == "warn":
                level = "warning"
            return {
                "level": level,
                "message": m.group(3),
                "source": "nginx",
                "stack_trace": None,
                "occurred_at": m.group(1).replace("/", "-"),
                "metadata": None,
            }

    # Plain text fallback
    return {
        "level": detect_level_from_text(line),
        "message": line,
        "source": None,
        "stack_trace": None,
        "occurred_at": None,
        "metadata": None,
    }


# --- File tail ---

class FileTailer:
    """Tail a file from last known position."""

    def __init__(self, path: str, fmt: str = "auto"):
        self.path = path
        self.fmt = fmt
        self._position = 0

    def set_position(self, pos: int):
        self._position = pos

    def get_position(self) -> int:
        return self._position

    def read_new_lines(self) -> list[dict]:
        """Read new lines from file since last position."""
        results = []
        try:
            with open(self.path, "r", errors="replace") as f:
                # Check if file was truncated/rotated
                f.seek(0, 2)  # end
                file_size = f.tell()
                if file_size < self._position:
                    self._position = 0  # file rotated

                f.seek(self._position)
                for line in f:
                    parsed = parse_line(line, self.fmt)
                    if parsed:
                        results.append(parsed)
                self._position = f.tell()
        except FileNotFoundError:
            logger.warning("Arquivo nao encontrado: %s", self.path)
        except Exception as e:
            logger.error("Erro ao ler %s: %s", self.path, e)
        return results


# --- Sender ---

class MemoraeSender:
    """Sends log batches to the Memora API."""

    def __init__(self, url: str, token: str):
        self.url = url.rstrip("/") + "/api/logs/ingest"
        self.token = token
        self._retry_delay = 1

    def send(self, logs: list[dict]) -> bool:
        if not logs:
            return True
        payload = {"logs": logs}
        try:
            resp = requests.post(
                self.url,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.token}",
                    "Content-Type": "application/json",
                },
                timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json()
                logger.info(
                    "Enviados %d logs, %d para analise",
                    data.get("received", len(logs)),
                    data.get("queued_for_analysis", 0),
                )
                self._retry_delay = 1
                return True
            else:
                logger.error("Memora retornou %d: %s", resp.status_code, resp.text[:200])
                return False
        except requests.exceptions.ConnectionError:
            logger.warning("Memora offline — retry em %ds", self._retry_delay)
            time.sleep(self._retry_delay)
            self._retry_delay = min(self._retry_delay * 2, 60)
            return False
        except Exception as e:
            logger.error("Erro ao enviar: %s", e)
            return False


# --- Main loop ---

def run(config: dict):
    min_level = LEVEL_PRIORITY.get(config["filters"].get("min_level", "warning"), 2)
    batch_size = config.get("batch_size", 100)
    flush_interval = config.get("flush_interval", 5)

    sender = MemoraeSender(config["memora_url"], config["project_token"])
    state = load_state()

    # Setup tailers
    tailers: list[FileTailer] = []
    for source in config.get("sources", []):
        if source.get("type") == "file":
            path = source["path"]
            fmt = source.get("format", "auto")
            tailer = FileTailer(path, fmt)
            # Restore position
            saved_pos = state.get(f"file:{path}", 0)
            tailer.set_position(saved_pos)
            tailers.append(tailer)
            logger.info("Monitorando: %s (formato=%s, posicao=%d)", path, fmt, saved_pos)

    if not tailers:
        logger.error("Nenhuma fonte de log configurada")
        sys.exit(1)

    buffer: list[dict] = []
    last_flush = time.time()

    running = True
    def handle_signal(sig, frame):
        nonlocal running
        logger.info("Sinal recebido, finalizando...")
        running = False

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    logger.info("Memora Agent iniciado — monitorando %d fontes", len(tailers))

    while running:
        for tailer in tailers:
            new_entries = tailer.read_new_lines()
            for entry in new_entries:
                level_prio = LEVEL_PRIORITY.get(entry.get("level", "info"), 1)
                if level_prio >= min_level:
                    buffer.append(entry)

        # Flush conditions: batch full or interval elapsed
        now = time.time()
        should_flush = (
            len(buffer) >= batch_size
            or (buffer and now - last_flush >= flush_interval)
        )

        if should_flush:
            if sender.send(buffer):
                buffer.clear()
                last_flush = now
                # Save positions
                new_state = {}
                for t in tailers:
                    new_state[f"file:{t.path}"] = t.get_position()
                save_state(new_state)

        time.sleep(0.5)

    # Final flush
    if buffer:
        sender.send(buffer)
        new_state = {}
        for t in tailers:
            new_state[f"file:{t.path}"] = t.get_position()
        save_state(new_state)

    logger.info("Memora Agent finalizado")


def main():
    parser = argparse.ArgumentParser(description="Memora Agent — Monitor de logs")
    parser.add_argument("--config", default="config.yaml", help="Caminho do config.yaml")
    parser.add_argument("--log-file", default=None, help="Arquivo de log do agente")
    parser.add_argument("--verbose", action="store_true", help="Log detalhado")
    args = parser.parse_args()

    # Setup logging
    log_level = logging.DEBUG if args.verbose else logging.INFO
    handlers: list[logging.Handler] = [logging.StreamHandler()]
    if args.log_file:
        handlers.append(logging.FileHandler(args.log_file))

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        handlers=handlers,
    )

    config = load_config(args.config)
    run(config)


if __name__ == "__main__":
    main()
