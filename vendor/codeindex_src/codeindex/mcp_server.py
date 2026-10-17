"""Stdio MCP server — exposes codeindex tools to Claude and other MCP clients."""
from __future__ import annotations
import json
import sys
from pathlib import Path

from codeindex.index import build, load, find_index, INDEX_FILENAME
from codeindex.impact import compute_blast_radius
from codeindex.reporter import format_markdown
from codeindex.symbols import SYMBOL_INDEX_FILENAME

TOOLS = [
    {
        "name": "analyze_repo",
        "description": "Analyze a repository and build/refresh its codeindex.json dependency index.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Absolute or relative path to the repo root.",
                }
            },
            "required": ["repo_path"],
        },
    },
    {
        "name": "get_impact",
        "description": (
            "Return the blast-radius impact report for a specific file. "
            "Shows direct dependents, transitive dependents, blast score, and risk level. "
            "Call this before modifying any file to understand change impact."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file to assess (relative to repo root or absolute).",
                },
                "index_path": {
                    "type": "string",
                    "description": "Path to codeindex.json. Auto-discovered if omitted.",
                },
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "get_dependencies",
        "description": "Return the direct imports and imported-by list for a specific file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "Path to the file (relative to repo root or absolute).",
                },
                "index_path": {
                    "type": "string",
                    "description": "Path to codeindex.json. Auto-discovered if omitted.",
                },
            },
            "required": ["file_path"],
        },
    },
    {
        "name": "get_high_blast_files",
        "description": "Return all files whose blast score exceeds a threshold, sorted by score descending.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "threshold": {
                    "type": "number",
                    "description": "Minimum blast score to include. Default: 5.",
                },
                "index_path": {
                    "type": "string",
                    "description": "Path to codeindex.json. Auto-discovered if omitted.",
                },
            },
        },
    },
    {
        "name": "lookup_symbol",
        "description": (
            "Find where a function, class, struct, or other symbol is defined. "
            "Returns file path and line number via O(1) index lookup — no file scanning. "
            "Requires symbolindex.json (run build_symbol_index first)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string",
                    "description": "Exact symbol name to look up.",
                },
                "symbol_index_path": {
                    "type": "string",
                    "description": "Path to symbolindex.json. Auto-discovered if omitted.",
                },
            },
            "required": ["name"],
        },
    },
    {
        "name": "build_symbol_index",
        "description": (
            "Build or refresh the symbol index (symbolindex.json) for a repository. "
            "Extracts every function, class, struct, and type with file and line number. "
            "Run once after cloning or after major refactors, then use lookup_symbol."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "repo_path": {
                    "type": "string",
                    "description": "Absolute or relative path to the repo root.",
                },
            },
            "required": ["repo_path"],
        },
    },
]


def _resolve_index(index_path: str | None) -> dict:
    if index_path:
        return load(Path(index_path))
    discovered = find_index(Path.cwd())
    if not discovered:
        raise FileNotFoundError(
            f"No {INDEX_FILENAME} found. Run: codeindex analyze <repo>"
        )
    return load(discovered)


def _resolve_file_id(file_path: str, data: dict) -> str | None:
    fp = Path(file_path)
    node_ids = {n["id"] for n in data["nodes"]}
    if str(fp) in node_ids:
        return str(fp)
    # Try matching by suffix (relative path without leading ./)
    clean = str(fp).lstrip("./")
    for nid in node_ids:
        if nid.endswith(clean) or clean.endswith(nid):
            return nid
    return None


def _call_analyze_repo(params: dict) -> dict:
    repo_path = params["repo_path"]
    data = build(repo_path)
    return {
        "success": True,
        "files":   data["meta"]["total_files"],
        "loc":     data["meta"]["total_loc"],
        "languages": data["meta"].get("languages", []),
    }


def _call_get_impact(params: dict) -> dict:
    data = _resolve_index(params.get("index_path"))
    file_id = _resolve_file_id(params["file_path"], data)
    if not file_id:
        return {"error": f"File not found in index: {params['file_path']}"}

    blast_map = compute_blast_radius(data["nodes"], data["links"])
    blast = blast_map.get(file_id)
    if not blast:
        return {"error": f"No blast data for {file_id}"}

    total = len([n for n in data["nodes"] if not n.get("type") == "import"])
    report = format_markdown(file_id, blast, total)
    return {"file": file_id, "report": report, "blast_score": blast["blast_score"]}


def _call_get_dependencies(params: dict) -> dict:
    data = _resolve_index(params.get("index_path"))
    file_id = _resolve_file_id(params["file_path"], data)
    if not file_id:
        return {"error": f"File not found in index: {params['file_path']}"}

    node = next((n for n in data["nodes"] if n["id"] == file_id), None)
    if not node:
        return {"error": f"Node not found: {file_id}"}

    return {
        "file":        file_id,
        "imports":     node.get("imports", []),
        "imported_by": node.get("imported_by", []),
        "blast_score": node.get("blast_score", 0),
    }


def _call_get_high_blast_files(params: dict) -> dict:
    data = _resolve_index(params.get("index_path"))
    threshold = float(params.get("threshold", 5))
    results = [
        {
            "file":       n["id"],
            "blast_score": n.get("blast_score", 0),
            "direct":     n.get("direct_dependents", 0),
            "transitive": n.get("transitive_dependents", 0),
        }
        for n in data["nodes"]
        if n.get("blast_score", 0) >= threshold and n.get("type") != "import"
    ]
    results.sort(key=lambda x: x["blast_score"], reverse=True)
    return {"files": results, "count": len(results), "threshold": threshold}


def _find_symbol_index(start: Path) -> Path | None:
    for d in [start, *start.parents]:
        p = d / SYMBOL_INDEX_FILENAME
        if p.exists():
            return p
    return None


def _resolve_symbol_index(symbol_index_path: str | None) -> dict:
    if symbol_index_path:
        p = Path(symbol_index_path)
    else:
        p = _find_symbol_index(Path.cwd())
    if not p or not p.exists():
        raise FileNotFoundError(
            f"No {SYMBOL_INDEX_FILENAME} found. Run: codeindex symbols <repo>"
        )
    return json.loads(p.read_text())


def _call_lookup_symbol(params: dict) -> dict:
    sym_data = _resolve_symbol_index(params.get("symbol_index_path"))
    name = params["name"]
    matches = sym_data.get("symbols", {}).get(name, [])
    if not matches:
        return {"found": False, "name": name, "matches": []}
    return {
        "found": True,
        "name": name,
        "matches": [
            {
                "file":     m["file"],
                "line":     m["line"],
                "kind":     m.get("kind", "?"),
                "exported": m.get("exported", True),
                "methods":  m.get("methods", []),
            }
            for m in matches
        ],
    }


def _call_build_symbol_index(params: dict) -> dict:
    from codeindex.symbols import build_symbol_index as _build, write_standalone  # noqa: PLC0415
    repo_path = params["repo_path"]
    symbol_data = _build(repo_path)
    out = Path(repo_path) / SYMBOL_INDEX_FILENAME
    write_standalone(symbol_data, out)
    return {
        "success":       True,
        "total_symbols": symbol_data["meta"]["total_symbols"],
        "files":         len(symbol_data["file_symbols"]),
        "output":        str(out),
    }


_HANDLERS = {
    "analyze_repo":        _call_analyze_repo,
    "get_impact":          _call_get_impact,
    "get_dependencies":    _call_get_dependencies,
    "get_high_blast_files": _call_get_high_blast_files,
    "lookup_symbol":       _call_lookup_symbol,
    "build_symbol_index":  _call_build_symbol_index,
}


def _send(obj: dict) -> None:
    sys.stdout.write(json.dumps(obj) + "\n")
    sys.stdout.flush()


def _handle(msg: dict) -> dict | None:
    method  = msg.get("method", "")
    req_id  = msg.get("id")
    params  = msg.get("params", {})

    def ok(result):
        return {"jsonrpc": "2.0", "id": req_id, "result": result}

    def err(code, message):
        return {"jsonrpc": "2.0", "id": req_id, "error": {"code": code, "message": message}}

    if method == "initialize":
        return ok({
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {}},
            "serverInfo": {"name": "codeindex", "version": "0.1.0"},
        })

    if method == "notifications/initialized":
        return None  # no response for notifications

    if method == "tools/list":
        return ok({"tools": TOOLS})

    if method == "tools/call":
        tool_name = params.get("name")
        tool_args = params.get("arguments", {})
        handler = _HANDLERS.get(tool_name)
        if not handler:
            return err(-32601, f"Unknown tool: {tool_name}")
        try:
            result = handler(tool_args)
            return ok({
                "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
            })
        except Exception as e:
            return ok({
                "content": [{"type": "text", "text": f"Error: {e}"}],
                "isError": True,
            })

    if method == "ping":
        return ok({})

    return err(-32601, f"Method not found: {method}")


def serve() -> None:
    print("[codeindex MCP] ready on stdio", file=sys.stderr)
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            _send({"jsonrpc": "2.0", "id": None,
                   "error": {"code": -32700, "message": "Parse error"}})
            continue
        response = _handle(msg)
        if response is not None:
            _send(response)
