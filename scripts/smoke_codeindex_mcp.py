"""Exercise the vendored codeindex MCP server through JSON-RPC stdio."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def request(process: subprocess.Popen[str], request_id: int, method: str, params: dict | None = None) -> dict:
    assert process.stdin is not None and process.stdout is not None
    process.stdin.write(json.dumps({"jsonrpc": "2.0", "id": request_id, "method": method, "params": params or {}}) + "\n")
    process.stdin.flush()
    line = process.stdout.readline()
    if not line:
        stderr = process.stderr.read() if process.stderr else ""
        raise RuntimeError(f"MCP server exited without a response: {stderr}")
    response = json.loads(line)
    if "error" in response:
        raise RuntimeError(f"MCP {method} failed: {response['error']}")
    return response


def tool(process: subprocess.Popen[str], request_id: int, name: str, arguments: dict) -> dict:
    response = request(process, request_id, "tools/call", {"name": name, "arguments": arguments})
    result = response.get("result", {})
    if result.get("isError"):
        raise RuntimeError(f"MCP tool {name} failed: {result}")
    content = result.get("content", [])
    return json.loads(content[0]["text"]) if content else {}


def main() -> int:
    build = subprocess.run(
        [sys.executable, "-m", "src.cli", "build-code-index"], cwd=ROOT, check=False
    )
    if build.returncode:
        return build.returncode

    process = subprocess.Popen(
        [sys.executable, "-m", "src.cli", "mcp-codeindex"], cwd=ROOT,
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
    )
    try:
        initialized = request(process, 1, "initialize", {
            "protocolVersion": "2024-11-05", "capabilities": {},
            "clientInfo": {"name": "repo-smoke", "version": "1"},
        })
        if "tools" not in initialized.get("result", {}).get("capabilities", {}):
            raise RuntimeError("MCP initialize response did not advertise tools")
        assert process.stdin is not None
        process.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
        process.stdin.flush()
        tools = request(process, 2, "tools/list").get("result", {}).get("tools", [])
        available = {entry["name"] for entry in tools}
        required = {"lookup_symbol", "get_impact", "get_dependencies"}
        if not required.issubset(available):
            raise RuntimeError(f"Missing MCP tools: {sorted(required - available)}")
        symbol = tool(process, 3, "lookup_symbol", {"name": "cmd_build_code_index"})
        impact = tool(process, 4, "get_impact", {"file_path": "src/cli.py"})
        dependencies = tool(process, 5, "get_dependencies", {"file_path": "src/cli.py"})
        if not symbol.get("found") or not impact.get("file") or not dependencies.get("file"):
            raise RuntimeError("One or more required MCP tools returned incomplete data")
        print("MCP smoke passed: lookup_symbol, get_impact, get_dependencies")
        return 0
    finally:
        if process.stdin:
            process.stdin.close()
        process.wait(timeout=10)


if __name__ == "__main__":
    raise SystemExit(main())
