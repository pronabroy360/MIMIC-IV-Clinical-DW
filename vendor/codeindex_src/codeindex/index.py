"""Build and persist codeindex.json in the target repo root."""
from __future__ import annotations
import json
import sys
from pathlib import Path

from codeindex.analyze import analyze
from codeindex.impact import compute_blast_radius, enrich_nodes, enrich_links

INDEX_FILENAME = "codeindex.json"


def build(repo_path: str, output: Path | None = None) -> dict:
    root = Path(repo_path).resolve()
    data = analyze(str(root))

    blast = compute_blast_radius(data["nodes"], data["links"])
    enrich_nodes(data["nodes"], blast)
    enrich_links(data["nodes"], data["links"])

    # Store blast map in meta for quick lookup
    data["meta"]["indexed"] = True

    dest = output or (root / INDEX_FILENAME)
    dest.write_text(json.dumps(data, indent=2))

    meta = data["meta"]
    langs_str = ", ".join(meta.get("languages", ["unknown"]))
    print(
        f"Indexed {meta['total_files']} files, {meta['total_loc']} LOC "
        f"[{langs_str}] → {dest}",
        file=sys.stderr,
    )
    return data


def load(index_path: Path) -> dict:
    if not index_path.exists():
        raise FileNotFoundError(
            f"{index_path} not found — run: codeindex analyze <repo>"
        )
    return json.loads(index_path.read_text())


def find_index(start: Path) -> Path | None:
    """Walk up from start looking for codeindex.json."""
    current = start.resolve()
    for _ in range(10):
        candidate = current / INDEX_FILENAME
        if candidate.exists():
            return candidate
        parent = current.parent
        if parent == current:
            break
        current = parent
    return None
