import ast
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_source_segment(source: str, node: ast.AST) -> str:
    lines = source.splitlines()
    start = node.lineno - 1
    end = node.end_lineno
    return "\n".join(lines[start:end])


def _get_decorated_start(node: ast.AST) -> int:
    if hasattr(node, "decorator_list") and node.decorator_list:
        return node.decorator_list[0].lineno
    return node.lineno


def _get_source_with_decorators(source: str, node: ast.AST) -> str:
    lines = source.splitlines()
    start = _get_decorated_start(node) - 1
    end = node.end_lineno
    return "\n".join(lines[start:end])


def _extract_function(source: str, node: ast.FunctionDef | ast.AsyncFunctionDef, file_path: str) -> dict:
    start_line = _get_decorated_start(node)
    return {
        "chunk_type": "function",
        "chunk_name": node.name,
        "content": _get_source_with_decorators(source, node),
        "start_line": start_line,
        "end_line": node.end_lineno,
        "docstring": ast.get_docstring(node),
        "file_path": file_path,
    }


def _extract_class(source: str, node: ast.ClassDef, file_path: str) -> dict:
    start_line = _get_decorated_start(node)
    return {
        "chunk_type": "class",
        "chunk_name": node.name,
        "content": _get_source_with_decorators(source, node),
        "start_line": start_line,
        "end_line": node.end_lineno,
        "docstring": ast.get_docstring(node),
        "file_path": file_path,
    }


def _extract_toplevel(source: str, tree: ast.Module, file_path: str) -> dict | None:
    """Extrai código top-level (imports, constantes, etc) fora de funções/classes."""
    lines = source.splitlines()
    defined_ranges = set()
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = _get_decorated_start(node) - 1
            end = node.end_lineno
            for i in range(start, end):
                defined_ranges.add(i)

    toplevel_lines = []
    for i, line in enumerate(lines):
        if i not in defined_ranges:
            toplevel_lines.append((i, line))

    non_empty = [(i, l) for i, l in toplevel_lines if l.strip()]
    if len(non_empty) <= 5:
        return None

    content = "\n".join(l for _, l in toplevel_lines)
    first_line = non_empty[0][0] + 1
    last_line = non_empty[-1][0] + 1

    return {
        "chunk_type": "module",
        "chunk_name": Path(file_path).stem,
        "content": content.strip(),
        "start_line": first_line,
        "end_line": last_line,
        "docstring": ast.get_docstring(tree),
        "file_path": file_path,
    }


def chunk_file_generic(file_path: str, max_lines: int = 80) -> list[dict]:
    """Chunker genérico para arquivos não-Python. Divide por blocos de linhas."""
    try:
        source = Path(file_path).read_text(encoding="utf-8")
    except Exception as e:
        logger.error(f"Erro ao ler {file_path}: {e}")
        return []

    lines = source.splitlines()
    if not lines or not source.strip():
        return []

    # Arquivo pequeno: chunk único
    if len(lines) <= max_lines:
        return [{
            "chunk_type": "module",
            "chunk_name": Path(file_path).stem,
            "content": source,
            "start_line": 1,
            "end_line": len(lines),
            "docstring": None,
            "file_path": file_path,
        }]

    # Arquivo grande: divide em blocos
    chunks = []
    for i in range(0, len(lines), max_lines):
        block = lines[i:i + max_lines]
        content = "\n".join(block)
        if not content.strip():
            continue
        part = i // max_lines + 1
        chunks.append({
            "chunk_type": "module",
            "chunk_name": f"{Path(file_path).stem}_part{part}",
            "content": content,
            "start_line": i + 1,
            "end_line": min(i + max_lines, len(lines)),
            "docstring": None,
            "file_path": file_path,
        })

    return chunks


def chunk_file(file_path: str, source: str | None = None) -> list[dict]:
    if source is None:
        try:
            source = Path(file_path).read_text(encoding="utf-8")
        except Exception as e:
            logger.error(f"Erro ao ler {file_path}: {e}")
            return []

    try:
        tree = ast.parse(source, filename=file_path)
    except SyntaxError as e:
        logger.warning(f"SyntaxError ao parsear {file_path}: {e}")
        return []

    chunks: list[dict] = []

    for node in ast.iter_child_nodes(tree):
        if isinstance(node, ast.ClassDef):
            chunks.append(_extract_class(source, node, file_path))
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            chunks.append(_extract_function(source, node, file_path))

    if not chunks:
        return [{
            "chunk_type": "module",
            "chunk_name": Path(file_path).stem,
            "content": source,
            "start_line": 1,
            "end_line": len(source.splitlines()),
            "docstring": ast.get_docstring(tree),
            "file_path": file_path,
        }]

    toplevel = _extract_toplevel(source, tree, file_path)
    if toplevel:
        chunks.insert(0, toplevel)

    return chunks
