from app.core.chunker import chunk_file


def test_functions_extracted(tmp_path):
    source = '''
def greet(name: str) -> str:
    """Sauda o usuário."""
    return f"Olá, {name}!"


def add(a: int, b: int) -> int:
    return a + b
'''
    f = tmp_path / "funcs.py"
    f.write_text(source, encoding="utf-8")

    chunks = chunk_file(str(f))
    functions = [c for c in chunks if c["chunk_type"] == "function"]

    assert len(functions) == 2
    assert functions[0]["chunk_name"] == "greet"
    assert functions[0]["docstring"] == "Sauda o usuário."
    assert functions[1]["chunk_name"] == "add"
    assert functions[1]["docstring"] is None


def test_class_with_methods(tmp_path):
    source = '''
class Calculator:
    """Uma calculadora simples."""

    def add(self, a, b):
        return a + b

    def subtract(self, a, b):
        return a - b
'''
    f = tmp_path / "calc.py"
    f.write_text(source)

    chunks = chunk_file(str(f))
    classes = [c for c in chunks if c["chunk_type"] == "class"]

    assert len(classes) == 1
    assert classes[0]["chunk_name"] == "Calculator"
    assert classes[0]["docstring"] == "Uma calculadora simples."
    assert "def add" in classes[0]["content"]
    assert "def subtract" in classes[0]["content"]

    # Métodos NÃO devem virar chunks separados
    functions = [c for c in chunks if c["chunk_type"] == "function"]
    assert len(functions) == 0


def test_empty_file_becomes_module(tmp_path):
    source = 'import os\nTIMEOUT = 30\n'
    f = tmp_path / "constants.py"
    f.write_text(source)

    chunks = chunk_file(str(f))

    assert len(chunks) == 1
    assert chunks[0]["chunk_type"] == "module"
    assert chunks[0]["chunk_name"] == "constants"


def test_syntax_error_returns_empty(tmp_path):
    f = tmp_path / "broken.py"
    f.write_text("def broken(\n")

    chunks = chunk_file(str(f))
    assert chunks == []


def test_toplevel_code_chunk(tmp_path):
    source = '''import os
import sys
import json
import logging
from pathlib import Path
from dataclasses import dataclass

logger = logging.getLogger(__name__)
BASE_DIR = Path(__file__).parent
CONFIG_PATH = BASE_DIR / "config.json"


def process():
    pass
'''
    f = tmp_path / "app.py"
    f.write_text(source)

    chunks = chunk_file(str(f))
    modules = [c for c in chunks if c["chunk_type"] == "module"]
    functions = [c for c in chunks if c["chunk_type"] == "function"]

    assert len(functions) == 1
    assert len(modules) == 1
    assert "import os" in modules[0]["content"]


def test_decorators_included(tmp_path):
    source = '''
@app.route("/test")
@login_required
def test_endpoint():
    return "ok"
'''
    f = tmp_path / "routes.py"
    f.write_text(source)

    chunks = chunk_file(str(f))
    func = [c for c in chunks if c["chunk_type"] == "function"][0]

    assert "@app.route" in func["content"]
    assert "@login_required" in func["content"]
    assert func["start_line"] < func["end_line"]
