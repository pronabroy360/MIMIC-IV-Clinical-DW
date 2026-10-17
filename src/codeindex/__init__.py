"""Deprecated regex prototype; use the vendored ``codeindex`` CLI instead.

The prototype is retained for source compatibility only. It is not used by the
project CLI and does not produce the dependency or symbol indexes used by MCP.
"""

import warnings

warnings.warn(
    "src.codeindex is deprecated; use `python -m src.cli build-code-index` instead",
    DeprecationWarning,
    stacklevel=2,
)
