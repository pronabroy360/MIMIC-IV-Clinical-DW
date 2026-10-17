from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CodeIndex:
    raw: dict[str, Any]

    @property
    def files(self) -> list[dict[str, Any]]:
        return list(self.raw.get("files") or [])

    @property
    def symbols(self) -> list[dict[str, Any]]:
        return list(self.raw.get("symbols") or [])

    @property
    def root(self) -> str:
        return str(self.raw.get("root") or "")


def load_code_index(index_path: Path) -> CodeIndex:
    data = json.loads(index_path.read_text(encoding="utf-8"))
    return CodeIndex(raw=data)


def _score_file_by_terms(file_entry: dict[str, Any], terms: list[str]) -> int:
    text_path = str(file_entry.get("path") or "").lower()
    score = int(file_entry.get("keyword_hit_score") or 0)
    for t in terms:
        if t in text_path:
            score += 10
    return score


def search_index(
    index: CodeIndex,
    query: str,
    top_k: int = 12,
) -> list[dict[str, Any]]:
    terms = [t for t in query.lower().replace("/", " ").split() if t.strip()]
    if not terms:
        return []
    scored: list[tuple[int, dict[str, Any]]] = []
    for f in index.files:
        score = _score_file_by_terms(f, terms)
        if score > 0:
            scored.append((score, f))
    scored.sort(key=lambda x: x[0], reverse=True)
    return [f for _, f in scored[:top_k]]


def find_symbol(index: CodeIndex, symbol_name: str, top_k: int = 10) -> list[dict[str, Any]]:
    name = symbol_name.strip()
    if not name:
        return []
    matches = [s for s in index.symbols if str(s.get("name") or "") == name]
    # Keep stable order as indexed.
    return matches[:top_k]


def project_map(index: CodeIndex) -> dict[str, Any]:
    """
    Provide a compact project map derived from file + symbol metadata.
    """
    files = index.files
    by_dir: dict[str, int] = {}
    for f in files:
        p = str(f.get("path") or "")
        dir_name = p.split("/", 1)[0] if "/" in p else ""
        by_dir[dir_name] = by_dir.get(dir_name, 0) + 1

    # Heuristic: identify main "surfaces" if relevant files exist.
    surfaces: list[str] = []
    paths = {str(f.get("path") or "") for f in files}
    for cand in ("src/api/main.py", "src/cli.py"):
        if cand in paths:
            surfaces.append(cand)

    return {
        "root": index.root,
        "file_count": len(files),
        "dir_summary": sorted(by_dir.items(), key=lambda x: x[1], reverse=True),
        "known_surfaces": surfaces,
    }
