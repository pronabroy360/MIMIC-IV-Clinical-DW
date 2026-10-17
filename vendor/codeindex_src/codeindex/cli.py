"""codeindex CLI entry point."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path


def _cmd_analyze(args: argparse.Namespace) -> None:
    from codeindex.index import build
    repo = args.repo
    output = Path(args.output) if args.output else None

    if args.watch:
        try:
            from watchdog.observers import Observer
            from watchdog.events import FileSystemEventHandler
        except ImportError:
            print("watchdog not installed — run: pip install 'codeindex[watch]'", file=sys.stderr)
            sys.exit(1)

        import threading

        WATCHED_EXTS = {
            ".py", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs",
            ".rb", ".go", ".rs", ".java", ".kt", ".php",
            ".yml", ".yaml", ".sql", ".prisma",
        }
        dest = output or (Path(repo).resolve() / "codeindex.json")

        class _Watcher(FileSystemEventHandler):
            def __init__(self):
                self._timer = None

            def _rebuild(self):
                print("[watch] change detected, re-indexing…", file=sys.stderr)
                build(repo, dest)

            def on_modified(self, event):
                if event.is_directory:
                    return
                if Path(event.src_path).suffix in WATCHED_EXTS:
                    if self._timer:
                        self._timer.cancel()
                    self._timer = threading.Timer(1.0, self._rebuild)
                    self._timer.start()

        build(repo, dest)
        observer = Observer()
        observer.schedule(_Watcher(), repo, recursive=True)
        observer.start()
        print(f"[watch] watching {repo} — Ctrl+C to stop", file=sys.stderr)
        try:
            while True:
                import time
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()
    else:
        build(repo, output)


def _cmd_impact(args: argparse.Namespace) -> None:
    from codeindex.index import load, find_index, INDEX_FILENAME
    from codeindex.impact import compute_blast_radius
    from codeindex.reporter import format_stdout, format_markdown

    if args.index:
        index_path = Path(args.index)
    else:
        index_path = find_index(Path(args.file).parent)
        if not index_path:
            index_path = find_index(Path.cwd())
        if not index_path:
            print(
                f"No {INDEX_FILENAME} found. Run: codeindex analyze <repo>",
                file=sys.stderr,
            )
            sys.exit(1)

    data = load(index_path)
    node_ids = {n["id"] for n in data["nodes"]}

    # Resolve file_id
    fp = args.file
    file_id = None
    if fp in node_ids:
        file_id = fp
    else:
        clean = fp.lstrip("./")
        for nid in node_ids:
            if nid.endswith(clean) or clean.endswith(nid):
                file_id = nid
                break

    if not file_id:
        print(f"File not found in index: {fp}", file=sys.stderr)
        print("Available nodes (first 20):", file=sys.stderr)
        for nid in sorted(node_ids)[:20]:
            print(f"  {nid}", file=sys.stderr)
        sys.exit(1)

    blast_map = compute_blast_radius(data["nodes"], data["links"])
    blast = blast_map[file_id]
    total = len([n for n in data["nodes"] if n.get("type") != "import"])

    if args.out:
        report = format_markdown(file_id, blast, total)
        Path(args.out).write_text(report)
        print(f"Impact report written to {args.out}")
    elif args.json:
        print(json.dumps({
            "file":                 file_id,
            "blast_score":          blast["blast_score"],
            "direct_dependents":    blast["direct_dependents"],
            "transitive_dependents": blast["transitive_dependents"],
            "direct_ids":           blast["direct_ids"],
            "transitive_ids":       blast["transitive_ids"],
        }, indent=2))
    else:
        print(format_stdout(file_id, blast, total))


def _cmd_serve(args: argparse.Namespace) -> None:
    if args.mcp:
        from codeindex.mcp_server import serve
        serve()
    else:
        from codeindex.viz_server import serve
        output = Path(args.output) if getattr(args, "output", None) else None
        serve(
            repo_path=args.repo,
            port=args.port,
            watch=args.watch,
            output=output,
        )


def _cmd_symbols(args: argparse.Namespace) -> None:
    from codeindex.symbols import (
        build_symbol_index, write_standalone, write_inline, write_claude_md,
        SYMBOL_INDEX_FILENAME,
    )
    from codeindex.index import find_index, INDEX_FILENAME

    repo = Path(args.repo).resolve()
    symbol_data = build_symbol_index(str(repo))

    if args.inline:
        if args.index:
            index_path = Path(args.index)
        else:
            index_path = find_index(repo)
            if not index_path:
                print(
                    f"No {INDEX_FILENAME} found — run: codeindex analyze <repo> first, "
                    "or pass --index <path>",
                    file=sys.stderr,
                )
                sys.exit(1)
        write_inline(symbol_data, index_path)
    else:
        output = Path(args.output) if args.output else (repo / SYMBOL_INDEX_FILENAME)
        write_standalone(symbol_data, output)

    if args.claude_md:
        claude_path = Path(args.claude_md_path) if args.claude_md_path else (repo / "CLAUDE.md")
        write_claude_md(symbol_data, claude_path, exported_only=not args.all_symbols)


def _cmd_lookup(args: argparse.Namespace) -> None:
    from codeindex.mcp_server import _find_symbol_index, _resolve_symbol_index
    sym_data = _resolve_symbol_index(args.index)
    name = args.name
    matches = sym_data.get("symbols", {}).get(name, [])
    if not matches:
        print(f"Symbol `{name}` not found in index.", file=sys.stderr)
        sys.exit(1)
    if args.json:
        print(json.dumps({"name": name, "matches": matches}, indent=2))
    else:
        for m in matches:
            methods = f"  methods: {', '.join(m['methods'])}" if m.get("methods") else ""
            print(f"{m['file']}:{m['line']}  ({m.get('kind', '?')}){methods}")


def _cmd_dependencies(args: argparse.Namespace) -> None:
    from codeindex.index import load, find_index, INDEX_FILENAME
    if args.index:
        index_path = Path(args.index)
    else:
        index_path = find_index(Path(args.file).parent) or find_index(Path.cwd())
        if not index_path:
            print(f"No {INDEX_FILENAME} found. Run: codeindex analyze <repo>", file=sys.stderr)
            sys.exit(1)
    data = load(index_path)
    fp = args.file
    clean = fp.lstrip("./")
    node = next(
        (n for n in data["nodes"] if n["id"] == fp or n["id"].endswith(clean) or clean.endswith(n["id"])),
        None,
    )
    if not node:
        print(f"File not found in index: {fp}", file=sys.stderr)
        sys.exit(1)
    if args.json:
        print(json.dumps({
            "file":        node["id"],
            "imports":     node.get("imports", []),
            "imported_by": node.get("imported_by", []),
            "blast_score": node.get("blast_score", 0),
        }, indent=2))
    else:
        print(f"File: {node['id']}  (blast score: {node.get('blast_score', 0):.1f})")
        imports = node.get("imports", [])
        imported_by = node.get("imported_by", [])
        print(f"\nImports ({len(imports)}):")
        for f in imports:
            print(f"  {f}")
        print(f"\nImported by ({len(imported_by)}):")
        for f in imported_by:
            print(f"  {f}")


def _cmd_high_blast(args: argparse.Namespace) -> None:
    from codeindex.index import load, find_index, INDEX_FILENAME
    if args.index:
        index_path = Path(args.index)
    else:
        index_path = find_index(Path.cwd())
        if not index_path:
            print(f"No {INDEX_FILENAME} found. Run: codeindex analyze <repo>", file=sys.stderr)
            sys.exit(1)
    data = load(index_path)
    threshold = args.threshold
    results = sorted(
        [n for n in data["nodes"] if n.get("blast_score", 0) >= threshold and n.get("type") != "import"],
        key=lambda n: n["blast_score"], reverse=True,
    )
    if args.json:
        print(json.dumps({"threshold": threshold, "count": len(results), "files": [
            {"file": n["id"], "blast_score": n["blast_score"],
             "direct": n.get("direct_dependents", 0), "transitive": n.get("transitive_dependents", 0)}
            for n in results
        ]}, indent=2))
    else:
        print(f"Files with blast score ≥ {threshold}  ({len(results)} found)\n")
        for n in results:
            print(f"  {n['blast_score']:>6.1f}  {n['id']}"
                  f"  ({n.get('direct_dependents', 0)}d / {n.get('transitive_dependents', 0)}t)")


def _cmd_install_hook(args: argparse.Namespace) -> None:
    from codeindex.hook import install
    install(
        repo_path=args.repo,
        threshold=args.threshold,
        strict=args.strict,
        remove=args.remove,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="codeindex",
        description="Repo dependency analyzer with blast-radius impact scoring.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    # ── analyze ────────────────────────────────────────────────────────────
    p_analyze = sub.add_parser("analyze", help="Analyze a repo and write codeindex.json")
    p_analyze.add_argument("repo", nargs="?", default=".", help="Path to repo root (default: .)")
    p_analyze.add_argument("--output", help="Output path (default: <repo>/codeindex.json)")
    p_analyze.add_argument("--watch", action="store_true", help="Re-index on file changes")

    # ── impact ─────────────────────────────────────────────────────────────
    p_impact = sub.add_parser("impact", help="Show blast-radius impact for a file")
    p_impact.add_argument("file", help="File path to assess")
    p_impact.add_argument("--index", help="Path to codeindex.json (auto-discovered if omitted)")
    p_impact.add_argument("--out", help="Write markdown report to this file")
    p_impact.add_argument("--json", action="store_true", help="Output raw JSON")

    # ── serve ──────────────────────────────────────────────────────────────
    p_serve = sub.add_parser("serve", help="Serve the visualization UI or run as MCP server")
    serve_mode = p_serve.add_mutually_exclusive_group()
    serve_mode.add_argument("--viz", action="store_true", default=True, help="Serve visualization UI (default)")
    serve_mode.add_argument("--mcp", action="store_true", help="Run as MCP stdio server")
    p_serve.add_argument("--repo", default=".", help="Repo to analyze (viz mode)")
    p_serve.add_argument("--port", type=int, default=8080, help="Port for viz server")
    p_serve.add_argument("--watch", action="store_true", help="Watch for file changes (viz mode)")
    p_serve.add_argument("--output", help="codeindex.json path override (viz mode)")

    # ── symbols ────────────────────────────────────────────────────────────────
    p_sym = sub.add_parser("symbols", help="Build a symbol index (functions, classes, exports)")
    p_sym.add_argument("repo", nargs="?", default=".", help="Path to repo root (default: .)")
    p_sym.add_argument(
        "--output", help="Output path for symbolindex.json (default: <repo>/symbolindex.json)"
    )
    p_sym.add_argument(
        "--inline", action="store_true",
        help="Embed symbols into codeindex.json nodes instead of a separate file",
    )
    p_sym.add_argument(
        "--index",
        help="Path to codeindex.json for --inline mode (auto-discovered if omitted)",
    )
    p_sym.add_argument(
        "--claude-md", dest="claude_md", action="store_true",
        help="Write compressed symbol summary to CLAUDE.md (exported symbols only by default)",
    )
    p_sym.add_argument(
        "--claude-md-path", dest="claude_md_path",
        help="Path to CLAUDE.md (default: <repo>/CLAUDE.md)",
    )
    p_sym.add_argument(
        "--all-symbols", dest="all_symbols", action="store_true",
        help="Include non-exported symbols in --claude-md output (default: exported only)",
    )

    # ── lookup ─────────────────────────────────────────────────────────────
    p_lookup = sub.add_parser("lookup", help="Find where a symbol is defined (file + line)")
    p_lookup.add_argument("name", help="Symbol name to look up")
    p_lookup.add_argument("--index", help="Path to symbolindex.json (auto-discovered if omitted)")
    p_lookup.add_argument("--json", action="store_true", help="Output raw JSON")

    # ── dependencies ───────────────────────────────────────────────────────
    p_deps = sub.add_parser("dependencies", help="Show imports and imported-by for a file")
    p_deps.add_argument("file", help="File path to inspect")
    p_deps.add_argument("--index", help="Path to codeindex.json (auto-discovered if omitted)")
    p_deps.add_argument("--json", action="store_true", help="Output raw JSON")

    # ── high-blast ─────────────────────────────────────────────────────────
    p_hb = sub.add_parser("high-blast", help="List files above a blast score threshold")
    p_hb.add_argument("--threshold", type=float, default=5.0, help="Minimum blast score (default: 5)")
    p_hb.add_argument("--index", help="Path to codeindex.json (auto-discovered if omitted)")
    p_hb.add_argument("--json", action="store_true", help="Output raw JSON")

    # ── install-hook ───────────────────────────────────────────────────────
    p_hook = sub.add_parser("install-hook", help="Install a pre-commit hook for impact warnings")
    p_hook.add_argument("--repo", default=".", help="Repo root (default: .)")
    p_hook.add_argument("--threshold", type=int, default=10, help="Blast score warning threshold (default: 10)")
    p_hook.add_argument("--strict", action="store_true", help="Block commit when threshold exceeded")
    p_hook.add_argument("--remove", action="store_true", help="Remove the installed hook")

    return parser


def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()

    dispatch = {
        "analyze":      _cmd_analyze,
        "impact":       _cmd_impact,
        "serve":        _cmd_serve,
        "symbols":      _cmd_symbols,
        "lookup":       _cmd_lookup,
        "dependencies": _cmd_dependencies,
        "high-blast":   _cmd_high_blast,
        "install-hook": _cmd_install_hook,
    }
    dispatch[args.command](args)


if __name__ == "__main__":
    main()
