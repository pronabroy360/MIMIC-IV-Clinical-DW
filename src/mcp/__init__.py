"""Deprecated JSON-RPC prototype; use ``python -m src.cli mcp-codeindex``.

This package remains for source compatibility. The project CLI launches the
vendored codeindex MCP server with its complete tool protocol.
"""

import warnings

warnings.warn(
    "src.mcp is deprecated; use `python -m src.cli mcp-codeindex` instead",
    DeprecationWarning,
    stacklevel=2,
)
