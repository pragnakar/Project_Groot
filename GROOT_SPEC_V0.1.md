# Project Groot — v0.1 MVP Build Specification

**Prepared:** 2026-03-13
**Author:** Claude (Cowork instance) — for Claude Code execution
**Repo:** New repo — `github.com/pragnakar/Project_Groot` (to be created)
**First Groot app:** Deferred — sage/ will integrate from its own repo (Project Sage)
**App module interface:** Generalized — any developer or AI can fork and build their own Groot app
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
├── groot_apps/
│   └── _example/              ← Example app scaffold (ships with Groot)
│       ├── __init__.py
│       ├── loader.py          ← Minimal register() — one demo tool + one demo page
│       └── README.md          ← "Build Your First Groot App" guide
│
├── docs/
│   └── APP_MODULE_GUIDE.md    ← Developer guide: how to build a Groot app module
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

Domain apps register themselves with Groot at startup via a standardized protocol. **Groot ships domain-agnostic** — any developer or AI agent can fork the repo, create `groot_apps/{name}/loader.py`, and have a working app module.

### 7.1 The Protocol

```python
# groot/app_protocol.py

from typing import Protocol, runtime_checkable

@runtime_checkable
class AppProtocol(Protocol):
    """Every Groot app module must expose a loader that satisfies this protocol."""

    async def register(
        self,
        tool_registry: "ToolRegistry",
        page_server: "PageServer",
        store: "ArtifactStore"
    ) -> None:
        """Called by Groot runtime at startup. Register tools, pages, and any
        artifacts your app needs. Groot passes in the shared runtime services."""
        ...
```

### 7.2 Example App (ships with Groot)

```python
# groot_apps/_example/loader.py

from groot.tools import ToolRegistry
from groot.page_server import PageServer
from groot.artifact_store import ArtifactStore

async def register(tool_registry: ToolRegistry, page_server: PageServer, store: ArtifactStore):
    """Minimal example — one tool, one page. Copy this to start your own app."""

    @tool_registry.tool(name="example.hello", description="Returns a greeting")
    async def hello(name: str = "world") -> dict:
        return {"message": f"Hello, {name}!"}

    await page_server.register_static("example-demo", "pages/demo.jsx")
```

### 7.3 Groot Startup (Generalized)

```python
# groot/server.py

ENABLED_APPS = os.getenv("GROOT_APPS", "_example").split(",")

@app.on_event("startup")
async def startup():
    for app_name in ENABLED_APPS:
        module = importlib.import_module(f"groot_apps.{app_name}.loader")
        # Validate protocol compliance before calling register
        if not hasattr(module, 'register'):
            raise RuntimeError(f"App '{app_name}' missing register() in loader.py")
        await module.register(tool_registry, page_server, artifact_store)
```

### 7.4 Convention

| Item | Convention |
|---|---|
| Directory | `groot_apps/{app_name}/loader.py` |
| Entry point | `async register(tool_registry, page_server, store)` |
| Tool namespace | `{app_name}.{tool_name}` (e.g., `sage.solve_optimization`) |
| Page namespace | `{app_name}-{page_name}` (e.g., `sage-dashboard`) |
| Config | App reads its own env vars; Groot passes shared services only |
| Docs | Each app should include a `README.md` in its directory |

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

### Phase G4 — Sage App Module ❌ DEFERRED

> **Status:** Deferred to Project Sage's own repository.
> **Decision date:** 2026-03-13
> **Decided by:** Peter (human review)

**Rationale:** Sage is a domain-specific optimization engine with its own development lifecycle, dependency tree (sage-solver-core, PuLP, etc.), and release cadence. Coupling it into the Groot repo would violate Groot's core principle of domain-agnosticism. Instead:

1. **Groot ships as a clean, forkable runtime** — any developer or AI agent can clone it, drop in their own `groot_apps/{name}/loader.py`, and have a working LLM runtime without needing to understand or remove sage-specific code.
2. **Sage integrates with Groot as an external app module** — Project Sage will use the same ClickUp workflow pipeline and Groot's app module interface (`register()`) to plug in, but from its own repo.
3. **The generalized app module interface (G-APP) replaces G4** — instead of building one specific app, we build the scaffold and documentation that makes Groot usable by *any* app.

**What was G4 becomes:** Project Sage work tracked in its own ClickUp space, consuming Groot as a dependency.

**Original G4 tasks closed:**
- G4-1, G4-2, G4-3 → status COMPLETE with deferral comments

---

### Phase G-APP — Generalized App Module Interface (Replaces G4)

> **Status:** HUMAN-REVIEW-2 (ClickUp task 868hw9808)
> **Added:** 2026-03-13

**Objective:** Make Groot forkable by any developer or AI agent. Ship the generalized app module interface — the protocol, scaffold, documentation, and example loader that lets anyone build a Groot app without reading Groot internals.

**Why this exists:** When G4 (sage) was deferred, it revealed that Groot's app module interface (§7) was described only through a sage-specific example. A domain-agnostic runtime needs a domain-agnostic onboarding path. G-APP closes that gap.

**Branch:** `feature/g-app-module-interface`

**Deliverables:**

1. **App Module Protocol** — `groot/app_protocol.py`
   - `AppProtocol` (Python Protocol class): `register(tool_registry, page_server, store)` with full type hints
   - Startup lifecycle: `on_startup()` / `on_shutdown()` hooks
   - App metadata: name, version, description, author
   - Groot validates each loader against the protocol at startup — clear error messages if `register()` signature is wrong

2. **Example App Scaffold** — `groot_apps/_example/`
   - `loader.py` — minimal working `register()` with one demo tool + one demo page
   - `README.md` — step-by-step "Build Your First Groot App" guide
   - Serves as both documentation and integration test fixture

3. **App Discovery & Loading** — Updates to `groot/server.py`
   - `GROOT_APPS` env var → discover → validate protocol → call `register()`
   - Structured error reporting: missing loader, bad signature, import failure
   - Namespace isolation: app tools prefixed with app name (e.g., `sage.solve_optimization`)

4. **REST Endpoints for App Introspection**
   - `GET /api/apps` → list loaded apps with metadata
   - `GET /api/apps/{name}` → app detail: tools registered, pages registered, status

5. **Developer Documentation** — `docs/APP_MODULE_GUIDE.md`
   - The contract: what Groot gives you, what you provide
   - Directory layout convention: `groot_apps/{name}/loader.py`
   - Tool registration, page registration, store access patterns
   - Testing your app module independently

**Acceptance Criteria:**
- [ ] `groot_apps/_example/` loads successfully on startup with `GROOT_APPS=_example`
- [ ] Example app's demo tool callable via REST and MCP
- [ ] Example app's demo page renders at `/apps/_example-demo`
- [ ] `GET /api/apps` returns loaded app metadata
- [ ] A loader with wrong `register()` signature produces a clear error, not a traceback
- [ ] `APP_MODULE_GUIDE.md` is sufficient for a developer (or AI agent) to build a new app module without reading Groot source

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
| 9 | App module scope | Generalized, not sage-specific | G4 (sage) deferred to own repo. Groot ships domain-agnostic with example scaffold. Any dev/AI can fork and build. |
| 10 | App module protocol | Python Protocol class with runtime check | Validates loader at startup. Clear errors for bad signatures. Prevents runtime surprises. |

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
| Every LLM project builds its own FastAPI server | Fork Groot, add `groot_apps/{name}/loader.py`, ship |
| Each project reinvents storage | One artifact store, accumulated across all apps |
| No standard LLM tool interface | Validated tool registry with Pydantic models and MCP transport |
| No live UI without a build step | React shell + Babel CDN — LLM creates pages, they render instantly |
| No design review layer | Claude in Chat generates pages; human approves before they enter Groot |
| sage-cloud is a one-off app | sage integrates from its own repo as a Groot app module |
| New AI agents start from scratch | Any AI agent can fork Groot and have a runtime in minutes |

---

## 13. Resume Checklist (for Claude Code)

```
[ ] 1. Read this file (GROOT_SPEC_V0.1.md)
[ ] 2. Read groot_spec.md (Peter's original vision — understand the why)
[ ] 3. Read .build/AGENT.md, .build/SPEC.md, .build/BUILD_LOG.md
[ ] 4. Check ClickUp Claude Code Queue (901113364003) for pending tasks
[ ] 5. Create new GitHub repo: Project_Groot (if not already created)
[ ] 6. Phase G1: groot/artifact_store.py → tools.py → server.py → auth.py → tests
[ ] 7. Phase G2: mcp_transport.py → stdio + SSE → entry points → tests
[ ] 8. Phase G3: page_server.py → React shell → integration tests
[ ] 9. Phase G-APP: app_protocol.py → _example scaffold → docs/APP_MODULE_GUIDE.md
[ ] 10. Tag groot-v0.1.0 after G3 + G-APP pass all acceptance criteria
```

**Note:** Phase G4 (sage) is deferred. Sage will integrate with Groot from Project Sage's own repo. Do not build sage-specific code in this repo.

---

*This spec was authored by Claude (Cowork) on 2026-03-13 based on Peter's groot_spec.md, BACK_TO_WORK_SPEC.md, and session discussion.*
*Updated 2026-03-13: G4 deferred to Project Sage. Added G-APP generalized app module interface. Repo structure and §7 revised for domain-agnostic forkability.*
*Architecture diagram available as groot_architecture.jsx (first Groot artifact, generated in-chat).*
