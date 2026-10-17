# TODO — codeindex + MCP integration (scheidydude/codeindex)

- [x] Use the real `scheidydude/codeindex` implementation (clean vendored source under `vendor/codeindex_src`; original checkout metadata is not embedded).
- [x] Wire `src/cli.py` to build:
  - `codeindex.json` (dependency/blast-radius index)
  - `symbolindex.json` (function/class symbol map)
- [x] Wire `src/cli.py` to start MCP via:
  - `codeindex serve --mcp --repo <root>` (stdio JSON-RPC tools)
- [x] Deprecate the custom prototype modules under `src/codeindex/` and `src/mcp/` (the CLI does not use them).
- [x] Document build, MCP launch, available tools, and Claude Code configuration in `README.md`.
- [x] Add `make smoke-codeindex-mcp` to build both indexes, launch the real vendored MCP server, and validate `lookup_symbol`, `get_impact`, and `get_dependencies` through JSON-RPC stdio.
- [x] Add a portable Claude Code MCP configuration example using the project Python interpreter and CLI.
