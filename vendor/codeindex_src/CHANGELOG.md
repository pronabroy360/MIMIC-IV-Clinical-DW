# Changelog

All notable changes to this project will be documented in this file.

## [0.2.0] - 2026-05-24

### Added
- `codeindex lookup <symbol>` — find where a symbol is defined (file + line)
- `codeindex dependencies <file>` — show imports and imported-by for a file
- `codeindex high-blast` — list files above a blast score threshold
- All three new commands support `--json` for machine-readable output
- `lookup_symbol` and `build_symbol_index` tools in MCP server
- CLI integration test suite (`benchmark/test_cli.py`) — 37 assertions covering happy path, `--json` output, error cases, and sort-order invariants
- MCP server integration test suite (`benchmark/test_mcp.py`) — all 6 MCP tools tested via real JSON-RPC stdio

### Changed
- MCP tests made repo-agnostic via fixture discovery from live index files
- `--claude-md` symbol section wrapped in `symbolindex` code fence

### Docs
- Claude coding workflows section in README
- `lookup`, `dependencies`, and `high-blast` CLI command documentation
- MCP registration instructions corrected to use `claude mcp add`

## [0.1.0] - Initial release

### Added
- Multi-language dependency analysis: Python, JavaScript/TypeScript, Go, Ruby, Rust, Java/Kotlin, PHP, CSS
- Blast-radius impact scoring — every file gets a score based on direct and transitive dependents
- `codeindex analyze <repo>` — analyze a repo and write `codeindex.json`
- `codeindex impact <file>` — show blast-radius impact report for a file
- `codeindex symbols <repo>` — build `symbolindex.json` with functions, classes, and exports; supports `--inline` and `--claude-md` modes
- `codeindex serve --mcp` — MCP stdio server exposing `analyze_repo`, `get_impact`, `get_dependencies`, `get_high_blast_files`, `build_symbol_index`, `lookup_symbol`
- `codeindex serve --viz` — visualization UI server
- `codeindex install-hook` — pre-commit hook for blast-radius warnings
- Phase 4: Docker, CI/CD, and schema analyzers
- Phase 5: monorepo and cross-language intelligence
- Apache 2.0 license
