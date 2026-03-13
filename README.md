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

# Custom port
python -m groot --port 8001

# Run MCP stdio transport (for Claude Desktop)
python -m groot --mcp-stdio

# Run tests
pytest
```

---

## Transport modes

| Mode | Command | Description |
|---|---|---|
| HTTP + SSE | `python -m groot` | REST API and MCP SSE on the same port (default) |
| stdio | `python -m groot --mcp-stdio` | MCP stdio for Claude Desktop |
| Both | `python -m groot --mcp-stdio --http` | stdio foreground, HTTP background |

---

## API

All tool routes require authentication via `X-Groot-Key` header or `?key=` query param.

| Route | Method | Description |
|---|---|---|
| `/health` | GET | Health check (no auth) |
| `/api/tools/write_blob` | POST | Write a blob to the artifact store |
| `/api/tools/read_blob` | POST | Read a blob by key |
| `/api/tools/list_blobs` | POST | List blobs with optional prefix filter |
| `/api/tools/delete_blob` | POST | Delete a blob |
| `/api/tools/create_page` | POST | Store a React JSX page |
| `/api/tools/update_page` | POST | Update an existing page |
| `/api/tools/list_pages` | POST | List all registered pages |
| `/api/tools/delete_page` | POST | Delete a page |
| `/api/tools/define_schema` | POST | Store a named JSON schema |
| `/api/tools/get_schema` | POST | Retrieve a schema by name |
| `/api/tools/list_schemas` | POST | List all schemas |
| `/api/tools/log_event` | POST | Append a structured log event |
| `/api/tools/call` | POST | Generic tool call endpoint |
| `/api/system/state` | GET | Runtime state (uptime, counts) |
| `/api/system/artifacts` | GET | Full artifact inventory |
| `/mcp/sse` | GET | MCP SSE transport (`?key=` required) |
| `/mcp/messages` | POST | MCP SSE message relay |

---

## MCP integration

### Claude Desktop (stdio)

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

### Remote SSE clients

Connect to `http://localhost:8000/mcp/sse?key=<api-key>` from any SSE-capable MCP client.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `GROOT_API_KEYS` | `groot_sk_dev_key_01` | Comma-separated API keys |
| `GROOT_DB_PATH` | `groot.db` | SQLite database path |
| `GROOT_ARTIFACT_DIR` | `artifacts` | Blob storage directory |
| `GROOT_APPS` | `sage` | Comma-separated app modules to load |
| `GROOT_HOST` | `0.0.0.0` | HTTP server host |
| `GROOT_PORT` | `8000` | HTTP server port |
| `GROOT_ENV` | `development` | `development` or `production` |

In `development` mode with no keys configured, auth is bypassed (dev convenience).
In `production` mode, empty `GROOT_API_KEYS` raises a 500 on startup.

---

## Project structure

```
groot/
  config.py          — Settings (pydantic-settings, .env)
  models.py          — Pydantic request/response models
  artifact_store.py  — Async SQLite CRUD (blobs, pages, schemas, events)
  auth.py            — API key middleware (FastAPI Depends)
  tools.py           — ToolRegistry + 14 core tools
  server.py          — FastAPI app, lifespan, all HTTP routes
  mcp_transport.py   — MCPBridge, stdio transport, SSE transport
  __main__.py        — Entry point (python -m groot)

groot-apps/
  sage/              — Sage domain app module (G4, planned)

groot-shell/         — React shell (G3, planned)

tests/
  conftest.py        — Shared fixtures (TestClient, temp DB, auth headers)
  test_models.py     — Pydantic model tests (31)
  test_artifact_store.py — SQLite CRUD tests (24)
  test_auth.py       — Auth middleware tests (9)
  test_tools.py      — ToolRegistry + core tool tests (22)
  test_server.py     — HTTP route integration tests (19)
  test_mcp_transport.py — MCPBridge + stdio tests (12)
  test_mcp_sse.py    — SSE route tests (8)
```

---

## Build phases

| Phase | Description | Status | Tests |
|---|---|---|---|
| G1 | Runtime core: FastAPI + SQLite + 14 tools + auth | **Complete** | 105 |
| G2 | MCP transport: stdio + SSE | **Complete** | 125 total |
| G3 | Page server + React shell | Planned | — |
| G4 | Sage app module | Planned | — |

---

## Architecture

See `GROOT_SPEC_V0.1.md` for the full spec and `groot_architecture.jsx` for the architecture diagram.
