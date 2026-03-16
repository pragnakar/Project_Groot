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

| Route | Method | Auth | Description |
|---|---|---|---|
| `/health` | GET | No | Health check |
| `/` | GET | No | React shell (groot-dashboard) |
| `/artifacts` | GET | No | React shell (groot-artifacts) |
| `/apps/{name}` | GET | No | React shell (named page) |
| `/api/pages` | GET | No | List all registered pages |
| `/api/pages/{name}/source` | GET | No | Raw JSX source for a page |
| `/api/pages/{name}/meta` | GET | No | Page metadata |
| `/api/tools/write_blob` | POST | Yes | Write a blob to the artifact store |
| `/api/tools/read_blob` | POST | Yes | Read a blob by key |
| `/api/tools/list_blobs` | POST | Yes | List blobs with optional prefix filter |
| `/api/tools/delete_blob` | POST | Yes | Delete a blob |
| `/api/tools/create_page` | POST | Yes | Store a React JSX page |
| `/api/tools/update_page` | POST | Yes | Update an existing page |
| `/api/tools/list_pages` | POST | Yes | List all registered pages |
| `/api/tools/delete_page` | POST | Yes | Delete a page |
| `/api/tools/define_schema` | POST | Yes | Store a named JSON schema |
| `/api/tools/get_schema` | POST | Yes | Retrieve a schema by name |
| `/api/tools/list_schemas` | POST | Yes | List all schemas |
| `/api/tools/log_event` | POST | Yes | Append a structured log event |
| `/api/tools/call` | POST | Yes | Generic tool call endpoint |
| `/api/system/state` | GET | Yes | Runtime state (uptime, counts) |
| `/api/system/artifacts` | GET | Yes | Full artifact inventory |
| `/api/apps` | GET | No | List loaded app modules |
| `/api/apps/{name}` | GET | No | App detail (tools, pages, status) |
| `/api/apps/{name}/health` | GET | No | App health check |
| `/api/apps/{name}` | DELETE | Yes | Unregister app, remove pages/tools; `?purge_data=true` deletes blobs+schemas; `?force=true` required for loaded apps + removes directory |
| `/api/apps/import` | POST | Yes | Upload `.zip` to install + hot-load an app module |
| `/mcp/sse` | GET | `?key=` | MCP SSE transport |
| `/mcp/messages` | POST | — | MCP SSE message relay |

---

## MCP integration

### Claude Desktop (stdio)

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "groot": {
      "command": "/opt/anaconda3/bin/python",
      "args": ["-m", "groot", "--mcp-stdio"],
      "cwd": "/path/to/Project_Groot",
      "env": {
        "GROOT_DB_PATH": "/path/to/Project_Groot/groot.db",
        "GROOT_ARTIFACT_DIR": "/path/to/Project_Groot/artifacts"
      }
    }
  }
}
```

> Use the **absolute path** to your Python executable (`which python`). Claude Desktop launches with a minimal PATH and won't find `python` otherwise.

Restart Claude Desktop. The 🔨 hammer icon confirms Groot tools are available.

**Test it:** ask Claude to `create a Groot page called hello with a live clock`. Then open `http://localhost:8000/#/apps/hello` (requires HTTP server running separately via `python -m groot`).

### Remote SSE clients

Connect to `http://localhost:8000/mcp/sse?key=<api-key>` from any SSE-capable MCP client.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `GROOT_API_KEYS` | `groot_sk_dev_key_01` | Comma-separated API keys |
| `GROOT_DB_PATH` | `groot.db` | SQLite database path |
| `GROOT_ARTIFACT_DIR` | `artifacts` | Blob storage directory |
| `GROOT_APPS` | `_example` | Comma-separated app modules to load |
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
  page_server.py     — PageServer: JSX delivery routes + static registration
  builtin_pages.py   — Built-in page JSX (groot-dashboard, groot-artifacts)
  __main__.py        — Entry point (python -m groot)

groot_apps/
  _example/          — Example app scaffold (ships with Groot)
    loader.py        — Minimal register() — one demo tool + one demo page
    README.md        — "Build Your First Groot App" guide

docs/
  APP_MODULE_GUIDE.md — Developer guide: how to build a Groot app module

groot-shell/
  index.html         — Self-contained React 18 shell (hash router, DynamicPage, Babel CDN)

groot/builtin_pages.py — Built-in pages registered at startup (dashboard + artifact browser)

tests/
  conftest.py        — Shared fixtures (TestClient, temp DB, auth headers)
  test_models.py     — Pydantic model tests (31)
  test_artifact_store.py — SQLite CRUD tests (24)
  test_auth.py       — Auth middleware tests (9)
  test_tools.py      — ToolRegistry + core tool tests (22)
  test_server.py     — HTTP route integration tests (19)
  test_mcp_transport.py — MCPBridge + stdio tests (12)
  test_mcp_sse.py    — SSE route tests (8)
  test_page_server.py   — Page server route tests (15)
  test_shell_integration.py — React shell + SPA route tests (8)
  test_g3_integration.py    — Full G3 integration tests (12)
```

---

## Build phases

| Phase | Description | Status | Tests |
|---|---|---|---|
| G1 | Runtime core: FastAPI + SQLite + 14 tools + auth | **Complete** | 105 |
| G2 | MCP transport: stdio + SSE | **Complete** | 125 total |
| G3 | Page server + React shell + built-in pages | **Complete** | 160 total |
| G-APP | Generalized app module interface + example scaffold + docs | **Complete** | — |
| Delete App | `DELETE /api/apps/{name}` with purge_data + force flags | **Complete** | 184 total |
| Import App | `POST /api/apps/import` — ZIP upload, validate, extract, hot-load | **Complete** | 198 total |
| ~~G4~~ | ~~Sage app module~~ | **Deferred** | — |

> **G4 note:** Sage is a domain-specific optimization engine with its own lifecycle. It was deferred to [Project Sage](https://github.com/pragnakar/Project_Sage) and will integrate with Groot as an external app module via the `register()` protocol. This keeps Groot clean, forkable, and domain-agnostic.

## Building your own Groot app

Groot ships with a generalized app module interface. Any developer or AI agent can build a Groot app:

1. Create `groot_apps/{your_app}/loader.py`
2. Implement `async def register(tool_registry, page_server, store)`
3. Register your tools and pages
4. Set `GROOT_APPS=your_app` in `.env`
5. Run `python -m groot`

See `docs/APP_MODULE_GUIDE.md` for the full guide, or copy `groot_apps/_example/` as a starting point.

---

## JSX page compatibility

The React shell handles all common LLM-generated JSX patterns automatically:

| Pattern | Handled |
|---|---|
| `function Page() { ... }` | Native |
| `export default function AnyName() { ... }` | Name captured, resolved |
| Bare JSX expression | Wrapped automatically |
| `import React from 'react'` | Stripped before transform |
| Destructured hooks (`useState`, `useEffect`, etc.) | Injected as named vars |
| `React.useState` style | Works natively |

No special prompt engineering needed — just ask Claude to build a page.

---

## Architecture

See `GROOT_SPEC_V0.1.md` for the full spec and `groot_architecture.jsx` for the architecture diagram.
