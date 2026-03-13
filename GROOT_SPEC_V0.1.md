# Project Groot — v0.1 MVP Build Specification

**Prepared:** 2026-03-13
**Author:** Claude (Cowork instance) — for Claude Code execution
**Repo:** New repo — `github.com/pragnakar/Project_Groot` (to be created)
**First Groot app:** sage/ (sage-cloud v0.2 built as a Groot domain module)
**Runway constraint:** Ship MVP in ≤5 days of Claude Code sessions

---

## 1. What Groot Is

Groot is a **LLM runtime environment**. It gives any MCP-compatible LLM agent a persistent execution layer consisting of:

- A web server it can add pages and routes to
- A persistent artifact store it can read and write
- A validated tool interface it calls through
- A pluggable domain module system for domain-specific tools and pages

**The LLM is always external.** Claude, ChatGPT, or any MCP client calls Groot tools over MCP (stdio or SSE) or REST HTTP. Groot never embeds a model.

**The flywheel:** Every artifact the LLM creates (React components, pages, blobs, schemas) is stored in Groot's artifact store. Each session builds on the last. The runtime becomes more capable as artifacts accumulate.

**The in-chat design pattern:** Claude in Chat (claude.ai/Cowork) generates React components as artifacts for human review. Approved components are staged to Groot via `create_page`. Chat is the design surface and QA layer before artifacts enter the runtime.

---

## 2. Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    LLM CLIENTS (external)                 │
│                                                          │
│  Claude Desktop  ChatGPT  Claude in Chat  Any MCP Client │
│  (MCP stdio)     (MCP SSE) (design surface) (HTTP)       │
└──────────────────────────┬──────────────────────────────┘
                           │ MCP / HTTP
                           ▼
┌─────────────────────────────────────────────────────────┐
│                   GROOT RUNTIME (FastAPI)                 │
│                                                          │
│  ┌─────────────────┐  ┌──────────────────┐              │
│  │  Tool Registry   │  │  MCP Transport   │              │
│  │  (pluggable)     │  │  (stdio + SSE)   │              │
│  └────────┬────────┘  └────────┬─────────┘              │
│           └──────────┬─────────┘                        │
│                      ▼                                   │
│           ┌──────────────────────┐                       │
│           │   Runtime Core       │                       │
│           │   validates · routes │                       │
│           │   sandboxes · auth   │                       │
│           └────┬──────────┬─────┘                       │
│                │          │                              │
│   ┌────────────▼──┐  ┌───▼────────────┐                 │
│   │ Artifact Store │  │  Page Server   │                 │
│   │ SQLite + fs    │  │  React shell   │                 │
│   │ components     │  │  dynamic routes│                 │
│   │ pages · blobs  │  │  /apps/:name   │                 │
│   │ schemas        │  │                │                 │
│   └───────────────┘  └────────────────┘                 │
└──────────────────────────┬──────────────────────────────┘
                           │ imports · registers tools
                           ▼
┌─────────────────────────────────────────────────────────┐
│                  GROOT APPS (domain modules)              │
│                                                          │
│  sage/            hermes/         athena/                │
│  (v0.2 — first)   (future)        (future)               │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Repository Structure

```
Project_Groot/
├── README.md
├── GROOT_SPEC.md              ← This document
├── pyproject.toml             ← groot-runtime package
│
├── groot/                     ← Core runtime (domain-agnostic)
│   ├── __init__.py
│   ├── server.py              ← FastAPI app, startup, lifespan
│   ├── tools.py               ← Core tool definitions + registry
│   ├── artifact_store.py      ← SQLite + filesystem persistence
│   ├── page_server.py         ← React shell + dynamic route serving
│   ├── auth.py                ← API key middleware
│   ├── mcp_transport.py       ← MCP stdio + SSE transport
│   ├── models.py              ← Pydantic schemas for all tool I/O
│   └── config.py              ← Settings (env vars, .env)
│
├── groot-apps/
│   └── sage/                  ← sage-cloud v0.2 as first Groot app
│       ├── __init__.py
│       ├── tools.py           ← SAGE-specific tools (solve, explain, etc.)
│       ├── pages/             ← SAGE React components
│       │   ├── dashboard.jsx
│       │   ├── result.jsx
│       │   └── sensitivity.jsx
│       └── loader.py          ← Registers sage tools + pages at startup
│
├── groot-shell/               ← React frontend shell
│   ├── index.html
│   ├── App.jsx                ← Route shell, loads registered pages
│   └── components/
│       └── ArtifactViewer.jsx ← Browse artifact store from UI
│
└── tests/
    ├── test_tools.py
    ├── test_artifact_store.py
    ├── test_page_server.py
    └── test_auth.py
```

---

## 4. Core Tool Interface

These are Groot's built-in tools — available to any LLM agent, domain-agnostic.

### 4.1 Storage Tools

```python
write_blob(key: str, data: str | bytes, content_type: str = "text/plain") -> BlobResult
# Writes a blob to the artifact store. Key format: "namespace/name"
# Returns: { key, size_bytes, created_at, url }

read_blob(key: str) -> BlobResult
# Reads a blob. Returns: { key, data, content_type, created_at }

list_blobs(prefix: str = "") -> list[BlobMeta]
# Lists blobs matching prefix. Returns: [{ key, size_bytes, created_at }]

delete_blob(key: str) -> bool
# Deletes a blob. Returns True if deleted.
```

### 4.2 Page Tools

```python
create_page(name: str, jsx_code: str, description: str = "") -> PageResult
# Stores a React component and registers it as a live route at /apps/{name}
# jsx_code: valid React JSX (functional component, default export)
# Returns: { name, url, created_at }

update_page(name: str, jsx_code: str) -> PageResult
# Replaces an existing page's JSX. Hot-updates the route.

list_pages() -> list[PageMeta]
# Lists all registered pages: [{ name, url, description, created_at, updated_at }]

delete_page(name: str) -> bool
```

### 4.3 Schema Tools

```python
define_schema(name: str, schema: dict) -> SchemaResult
# Stores a JSON schema under a name. Used for structured data validation.

get_schema(name: str) -> SchemaResult

list_schemas() -> list[SchemaMeta]
```

### 4.4 System Tools

```python
log_event(message: str, level: str = "info", context: dict = {}) -> LogResult
# Appends a structured log entry. Returns: { id, timestamp, message, level }

get_system_state() -> SystemState
# Returns: { uptime, artifact_count, page_count, blob_count, registered_apps }

list_artifacts() -> ArtifactSummary
# Returns full inventory: pages, blobs, schemas, recent logs
```

---

## 5. Artifact Store — Data Model

SQLite database at `groot.db` + `artifacts/` filesystem directory.

```sql
-- Blobs: arbitrary data keyed by namespace/name
CREATE TABLE blobs (
    key         TEXT PRIMARY KEY,
    data        BLOB NOT NULL,
    content_type TEXT NOT NULL DEFAULT 'text/plain',
    size_bytes  INTEGER NOT NULL,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

-- Pages: React components registered as routes
CREATE TABLE pages (
    name        TEXT PRIMARY KEY,
    jsx_code    TEXT NOT NULL,
    description TEXT NOT NULL DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL
);

-- Schemas: named JSON schemas
CREATE TABLE schemas (
    name        TEXT PRIMARY KEY,
    schema_json TEXT NOT NULL,
    created_at  TEXT NOT NULL
);

-- Event log: structured history
CREATE TABLE events (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT NOT NULL,
    level       TEXT NOT NULL DEFAULT 'info',
    message     TEXT NOT NULL,
    context_json TEXT NOT NULL DEFAULT '{}'
);
```

---

## 6. Page Server — React Shell

Groot serves a single React shell application that dynamically loads registered pages.

**How it works:**
1. LLM calls `create_page("my-dashboard", jsx_code)`
2. Groot stores the JSX in the artifact store
3. Page server exposes `GET /api/pages/my-dashboard/source` → returns the JSX
4. React shell fetches and renders it at `/apps/my-dashboard`

**Shell routing:**
```
/                    ← Groot dashboard (built-in): lists pages, recent activity
/apps/:name          ← Renders registered page by name
/artifacts           ← Artifact browser (built-in): browse blobs, schemas
/docs                ← FastAPI auto-docs
```

**JSX delivery for MVP:**
For v0.1, use a simple eval-based approach: the shell fetches raw JSX, transforms it with Babel standalone (CDN), and renders it. This avoids a build step. It is not production-safe but is correct for MVP prototype validation.

For v0.2, replace with a proper module federation or Vite-based dynamic import approach.

---

## 7. App Module Interface

Domain apps register themselves with Groot at startup.

```python
# groot-apps/sage/loader.py

from groot.tools import ToolRegistry
from groot.page_server import PageServer

def register(tool_registry: ToolRegistry, page_server: PageServer):
    """Called by Groot runtime at startup when sage app is enabled."""

    # Register SAGE-specific tools
    tool_registry.register(solve_optimization)
    tool_registry.register(explain_solution)
    tool_registry.register(check_feasibility)
    tool_registry.register(read_data_file)
    tool_registry.register(solve_from_file)
    tool_registry.register(generate_template)
    tool_registry.register(suggest_relaxations)

    # Register SAGE-specific pages
    page_server.register_static("sage-dashboard", "pages/dashboard.jsx")
    page_server.register_static("sage-result", "pages/result.jsx")
    page_server.register_static("sage-sensitivity", "pages/sensitivity.jsx")
```

Groot's startup:
```python
# groot/server.py

ENABLED_APPS = os.getenv("GROOT_APPS", "sage").split(",")

@app.on_event("startup")
async def startup():
    for app_name in ENABLED_APPS:
        module = importlib.import_module(f"groot_apps.{app_name}.loader")
        module.register(tool_registry, page_server)
```

---

## 8. Authentication

**v0.1 MVP:** API key middleware only.

```python
# Header: X-Groot-Key: groot_sk_xxxxxxxxxxxx
# Query param (for MCP SSE): ?key=groot_sk_xxxxxxxxxxxx
# Keys stored in GROOT_API_KEYS env var (comma-separated)
# No database needed for MVP
```

---

## 9. Build Phases

### Phase G1 — Runtime Core (Hours 1-10)

```
Branch: feature/g1-runtime-core

1. New repo: Project_Groot
2. pyproject.toml: fastapi, uvicorn, pydantic, python-dotenv, aiosqlite
3. groot/config.py — Settings class
4. groot/models.py — All Pydantic schemas for tool I/O
5. groot/artifact_store.py — SQLite init, CRUD for blobs/pages/schemas/events
6. groot/auth.py — API key middleware
7. groot/tools.py — All 12 core tools implemented against artifact_store
8. groot/server.py — FastAPI app, lifespan, tool routes, health check
9. Tests: test_tools.py, test_artifact_store.py, test_auth.py
10. Verify: POST /tools/write_blob → read back → list_blobs works end to end
```

### Phase G2 — MCP Transport (Hours 11-16)

```
Branch: feature/g2-mcp-transport

1. groot/mcp_transport.py — Register all 12 core tools as MCP tools
2. stdio transport (for Claude Desktop)
3. SSE transport (for ChatGPT + remote clients)
4. __main__.py entry point: uvicorn server + optional MCP stdio mode
5. Test: connect Claude Desktop to Groot, call write_blob and read_blob
```

### Phase G3 — Page Server + React Shell (Hours 17-26)

```
Branch: feature/g3-page-server

1. groot/page_server.py — Dynamic route registration, JSX delivery endpoint
2. groot-shell/ — React shell app (single index.html, no build step)
   - App.jsx: route shell, dynamic page loader
   - Babel standalone for JSX transform (CDN)
   - Built-in pages: Groot dashboard, artifact browser
3. Serve shell from FastAPI: GET / → index.html
4. Test: create_page("test", simple_jsx) → visit /apps/test → component renders
5. Test: update_page replaces component live
```

### Phase G4 — Sage App Module (Hours 27-38)

```
Branch: feature/g4-sage-app

1. groot-apps/sage/ package
2. sage/tools.py — Wrap sage-solver-core tools for Groot's tool registry
   - These are the SAME 7 tools from sage-solver-mcp/server.py
   - Adapt: replace module-level ServerState with per-request job state (from BACK_TO_WORK_SPEC.md job manager design)
3. sage/pages/ — Port sage-cloud web UI designs to Groot React pages:
   - dashboard.jsx — recent solves, quick-solve form
   - result.jsx — variable values, binding constraints, download
   - sensitivity.jsx — shadow prices, "what if" sliders
4. sage/loader.py — register() function
5. Update groot/server.py startup to load sage by default
6. Tests: full flow — LLM calls solve_optimization → result stored → /apps/sage-result renders it
7. Tag: groot-v0.1.0 + sage-v0.2.0
```

---

## 10. Key Design Decisions

| # | Decision | Choice | Rationale |
|---|---|---|---|
| 1 | LLM topology | External client | LLM calls Groot via MCP/HTTP. Never embedded. |
| 2 | UI framework | React | LLM codegen quality for JSX >> Flutter/Dart. Component reuse maps to artifact accumulation. |
| 3 | JSX delivery (MVP) | Babel standalone eval | No build step. Fast to ship. Replace in v0.2 with module federation. |
| 4 | Storage | SQLite + filesystem | Zero-dependency for MVP. Upgrade path to Postgres + S3. |
| 5 | MCP transport | stdio (v0.1) + SSE (v0.1) | Both. stdio for Claude Desktop, SSE for ChatGPT. |
| 6 | App modules | Import at startup | Simple, no service discovery overhead for MVP. |
| 7 | State isolation | Per-request (no module-level state) | Multi-app from day one. Learned from sage-mcp's ServerState limitation. |
| 8 | In-chat design flow | Claude chat → approve → create_page | Chat is Groot's design surface. Every page reviewed before entering artifact store. |

---

## 11. Design Rules (non-negotiable)

1. **Groot runtime never contains domain logic.** It knows nothing about optimization, translation, or governance. It provides a runtime. Apps provide domain tools.
2. **All LLM interactions go through validated tool calls.** No raw code execution in the runtime.
3. **Artifact store is append-friendly.** Prefer update operations over deletes. The flywheel depends on accumulation.
4. **State is per-request.** No module-level mutable state. Learned from sage-mcp v0.1.
5. **React shell has no build step in v0.1.** Babel standalone CDN only. Ship fast; optimize later.
6. **Every tool returns structured Pydantic models.** Never bare dicts or exceptions.

---

## 12. What Groot Unlocks

| Without Groot | With Groot |
|---|---|
| sage-cloud is a one-off FastAPI app | sage-cloud is a Groot app module — 30% the code |
| Hermes needs its own web server | Hermes registers tools + pages into Groot |
| Athena starts from scratch | Athena drops into Groot in days |
| Each project reinvents storage | One artifact store, accumulated across all apps |
| No design review layer | Claude in Chat generates pages; Peter approves before they enter Groot |

---

## 13. Resume Checklist (for Claude Code)

```
[ ] 1. Read this file (GROOT_SPEC_V0.1.md)
[ ] 2. Read groot_spec.md (Peter's original vision — understand the why)
[ ] 3. Read BACK_TO_WORK_SPEC.md (sage-cloud spec — this becomes Phase G4)
[ ] 4. Read HANDOFF.md (sage-solver-core architecture — don't re-implement anything)
[ ] 5. Create new GitHub repo: Project_Groot
[ ] 6. Start Phase G1: groot/artifact_store.py first, then tools.py, then server.py
[ ] 7. Follow phase protocol: build → test → verify → next phase
[ ] 8. Tag v0.1.0 after Phase G3. Phase G4 is sage v0.2.0 on top of Groot.
```

---

*This spec was authored by Claude (Cowork) on 2026-03-13 based on Peter's groot_spec.md, BACK_TO_WORK_SPEC.md, and session discussion.*
*Architecture diagram available as groot_architecture.jsx (first Groot artifact, generated in-chat).*
