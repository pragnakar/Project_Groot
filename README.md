# Project Groot

Domain-agnostic LLM runtime environment.

Groot gives any MCP-compatible LLM agent a persistent execution layer: a SQLite artifact store, a validated tool interface (14 core tools), a React page server, and a pluggable domain module system. The LLM is always external — Groot never embeds a model.

---

## Quick start

```bash
# Install
pip install -e ".[dev]"

# Configure
cp .env.example .env

# Run HTTP server (REST API + SSE MCP transport on same port)
python -m groot

# Run MCP stdio transport (for Claude Desktop)
python -m groot --mcp-stdio

# Run tests
pytest
```

### Claude Desktop integration

Copy `mcp_config.example.json` into your Claude Desktop MCP config:

```json
{
  "mcpServers": {
    "groot": {
      "command": "python",
      "args": ["-m", "groot", "--mcp-stdio"],
      "env": { "GROOT_API_KEYS": "groot_sk_dev_key_01" }
    }
  }
}
```

### SSE MCP clients (remote)

Connect to `http://localhost:8000/mcp/sse?key=<api-key>` from any SSE-capable MCP client.

## Architecture

See `GROOT_SPEC_V0.1.md` for full spec and `groot_architecture.jsx` for the architecture diagram.

## Build phases

| Phase | Description | Status |
|---|---|---|
| G1 | Runtime core: FastAPI + SQLite + 14 tools + auth | Complete |
| G2 | MCP transport: stdio + SSE | Complete |
| G3 | Page server + React shell | Planned |
| G4 | sage/ app module (sage-cloud v0.2) | Planned |
