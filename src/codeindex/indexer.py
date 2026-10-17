from __future__ import annotations

import hashlib
import json
import os
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any


_PY_DEF_RE = re.compile(r"^def\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", re.MULTILINE)
_PY_CLASS_RE = re.compile(r"^class\s+([A-Za-z_][A-Za-z0-9_]*)\b", re.MULTILINE)


@dataclass(frozen=True)
class IndexedSymbol:
    name: str
    kind: str  # "def" | "class"
    file_path: str
    # Best-effort heuristic; not a real AST position.
    signature: str


def _sha1_text(text: str) -> str:
    return hashlib.sha1(text.encode("utf-8", errors="ignore")).hexdigest()


def _extract_python_symbols(text: str) -> list[IndexedSymbol]:
    symbols: list[IndexedSymbol] = []
    for m in _PY_CLASS_RE.finditer(text):
        name = m.group(1)
        symbols.append(
            IndexedSymbol(
                name=name,
                kind="class",
                file_path="",
                signature=f"class {name}",
            )
        )
    for m in _PY_DEF_RE.finditer(text):
        name = m.group(1)
        symbols.append(
            IndexedSymbol(
                name=name,
                kind="def",
                file_path="",
                signature=f"def {name}(...)",
            )
        )
    return symbols


def build_code_index(
    root_dir: Path,
    include_globs: list[str],
    exclude_dir_names: set[str] | None = None,
    max_file_bytes: int = 2_000_000,
) -> dict[str, Any]:
    """
    Build a lightweight JSON-serializable index of the repository.

    The index is intentionally heuristic-based (regex, keyword chunks) so it can
    work without extra dependencies.
    """
    exclude_dir_names = exclude_dir_names or {".git", "__pycache__", ".venv", "dist", "build", "outputs"}

    include_globs = include_globs or ["src/**/*.py", "docs/**/*.md", "tests/**/*.py"]

    files: list[Path] = []
    for pattern in include_globs:
        files.extend(root_dir.glob(pattern))

    seen: set[Path] = set()
    candidates: list[Path] = []
    for p in files:
        rp = p.resolve()
        if rp in seen:
            continue
        seen.add(rp)

        parts = set(p.parts)
        if exclude_dir_names.intersection(parts):
            continue
        candidates.append(p)

    index: dict[str, Any] = {
        "root": str(root_dir),
        "created_at": int(os.path.getmtime(root_dir)) if root_dir.exists() else None,
        "files": [],
        "symbols": [],
    }

    for path in sorted(candidates):
        try:
            stat = path.stat()
            if stat.st_size > max_file_bytes:
                continue
            raw = path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue

        file_entry: dict[str, Any] = {
            "path": str(path.relative_to(root_dir)),
            "language": "py" if path.suffix == ".py" else (path.suffix.lstrip(".") or "text"),
            "sha1": _sha1_text(raw),
            "size": stat.st_size,
        }

        # Basic chunking for keyword retrieval.
        lowered = raw.lower()
        keywords = [
            "class ",
            "def ",
            "router",
            "fastapi",
            "sql",
            "duckdb",
            "validate",
            "guardrail",
            "build_gold",
            "build_silver",
            "build_bronze",
            "mcp",
            "index",
        ]
        hit_count = sum(1 for kw in keywords if kw in lowered)
        file_entry["keyword_hit_score"] = hit_count

        # Extract Python symbols if applicable.
        if path.suffix == ".py":
            syms = _extract_python_symbols(raw)
            for s in syms:
                file_entry_rel = str(path.relative_to(root_dir))
                index["symbols"].append(
                    {
                        "name": s.name,
                        "kind": s.kind,
                        "file_path": file_entry_rel,
                        "signature": s.signature,
                    }
                )

        index["files"].append(file_entry)

        # Avoid storing whole file content in the index.
        # MCP tool can still serve file contents on demand.
    return index


def write_code_index(index: dict[str, Any], output_path: Path) -> Path:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(index, indent=2), encoding="utf-8")
    return output_path


def default_index_output(project_root: Path) -> Path:
    return project_root / "outputs/private/code_index/index.json"
