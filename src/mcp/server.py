from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

from src.codeindex.indexer import default_index_output, build_code_index, write_code_index
from src.codeindex.query import load_code_index, project_map, search_index, find_symbol
from src.core.paths import project_root


def _json_send(obj: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _json_recv() -> dict[str, Any] | None:
    line = sys.stdin.readline()
    if not line:
        return None
    return json.loads(line)


def _get_file_text(root: Path, file_path: str) -> str:
    # Prevent path traversal: only allow paths under root.
    p = (root / file_path).resolve()
    if root.resolve() not in p.parents and p != root.resolve():
        raise ValueError("Invalid file path")
    return p.read_text(encoding="utf-8", errors="ignore")


def ensure_index(index_path: Path) -> Path:
    if index_path.exists():
        return index_path
    root = project_root()
    index = build_code_index(
        root_dir=root,
        include_globs=["src/**/*.py", "docs/**/*.md", "tests/**/*.py", "README.md", "AGENTS.md"],
    )
    return write_code_index(index, index_path)


def run_stdio_server(index_path: Path | None = None) -> None:
    root = project_root()
    index_path = index_path or default_index_output(root)
    ensure_index(index_path)
    index = load_code_index(index_path)

    while True:
        msg = _json_recv()
        if msg is None:
            return

        req_id = msg.get("id")
        method = msg.get("method")
        params = msg.get("params") or {}

        try:
            if method == "project_map":
                result = project_map(index)
            elif method == "search_code":
                query = str(params.get("query") or "")
                top_k = int(params.get("top_k") or 12)
                result = search_index(index, query=query, top_k=top_k)
            elif method == "find_symbol":
                symbol = str(params.get("symbol") or "")
                top_k = int(params.get("top_k") or 10)
                result = find_symbol(index, symbol_name=symbol, top_k=top_k)
            elif method == "get_file":
                file_path = str(params.get("file_path") or "")
                result = {"path": file_path, "content": _get_file_text(root, file_path)}
            elif method == "rebuild_index":
                index_path_actual = ensure_index(index_path)
                index = load_code_index(index_path_actual)
                result = {"ok": True, "index_path": str(index_path_actual)}
            else:
                raise ValueError(f"Unknown method: {method}")

            _json_send({"jsonrpc": "2.0", "id": req_id, "result": result})
        except Exception as exc:
            _json_send(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32000, "message": str(exc)},
                }
            )


def main(argv: list[str] | None = None) -> int:
    # Simple CLI: `python -m src.mcp.server` will run with default index location.
    index_path_arg = None
    if argv:
        # Accept: --index-path <path>
        args = list(argv)
        if "--index-path" in args:
            i = args.index("--index-path")
            index_path_arg = Path(args[i + 1])

    run_stdio_server(index_path=index_path_arg)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
