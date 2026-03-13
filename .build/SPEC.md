# SPEC.md — Project Specification
# Project: Project Groot
# Version: 0.1 — Phase G1 Draft
# Last Updated: 2026-03-13

---

## Project Overview

Groot is a domain-agnostic LLM runtime environment built on FastAPI. It gives any MCP-compatible LLM agent a persistent execution layer: a SQLite-backed artifact store, a validated tool interface (12 core tools), a React page server, and a pluggable domain module system. The LLM is always external — Claude, ChatGPT, or any MCP client calls Groot over MCP (stdio or SSE) or REST HTTP. Groot never embeds a model. Domain tools and pages register at startup as app modules. `sage/` is the first Groot app, wrapping sage-solver-core as a Groot domain module.

---

## Goals

1. Ship a working Groot runtime (FastAPI + SQLite + 12 tools + MCP + React shell) in ≤5 Claude Code sessions
2. Deploy sage-cloud v0.2 as the first Groot app module, replacing the standalone sage-cloud app
3. Validate the flywheel: artifacts accumulated across sessions, pages registered and served live

## Non-Goals (v0.1)

- Multi-tenancy, user accounts, or role-based access (API key per deployment only)
- Vite/Webpack build pipeline — Babel standalone CDN only
- Database migration tooling — schema is created fresh on first startup
- Hermes, Athena, or any Groot app other than sage/
- Production-grade JSX sandboxing

---

## Architecture

### System Components

| Component | Description |
|---|---|
| `groot/server.py` | FastAPI app, lifespan, health check, tool routes, app module loader |
| `groot/artifact_store.py` | SQLite + filesystem CRUD for blobs, pages, schemas, events |
| `groot/tools.py` | 12 core tools implemented against artifact_store; tool registry |
| `groot/models.py` | Pydantic v2 schemas for all tool I/O |
| `groot/auth.py` | API key middleware (X-Groot-Key header or ?key= query param) |
| `groot/mcp_transport.py` | MCP stdio + SSE transport; registers all 12 tools as MCP tools |
| `groot/page_server.py` | Dynamic route registration; JSX delivery endpoint |
| `groot/config.py` | pydantic-settings Settings class; env var config |
| `groot-shell/` | React shell app — route shell, Babel standalone JSX eval, built-in pages |
| `groot-apps/sage/` | sage-cloud v0.2 as Groot app module — tools + pages + loader |

### Data Flow

1. LLM client (Claude Desktop, ChatGPT, HTTP) sends tool call over MCP or REST
2. `auth.py` middleware validates API key — 401 on failure
3. `tools.py` dispatches to correct tool function; validates input via Pydantic
4. Tool reads/writes `artifact_store.py` — SQLite + filesystem
5. Tool returns Pydantic model response
6. For pages: `page_server.py` serves JSX source; React shell fetches and Babel-evals it at `/apps/:name`

### Technology Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Runtime | FastAPI + uvicorn | Async, Pydantic-native, MCP-compatible |
| Storage | SQLite + filesystem (aiosqlite) | Zero-dependency for MVP; upgrade path to Postgres + S3 |
| Frontend | React + Babel standalone CDN | No build step; LLM JSX codegen quality; component accumulation |
| MCP transport | stdio + SSE | Both: stdio for Claude Desktop, SSE for ChatGPT/remote |
| App modules | Import at startup via `importlib` | Simple; no service discovery overhead for MVP |
| State | Per-request only | Multi-app safety; learned from sage-mcp ServerState limitation |
| Auth | API key (env var) | Sufficient for MVP single-deployment |

---

## Phase Plan

### Phase G1 — Runtime Core (CURRENT)

**Objective:** Build the FastAPI app, SQLite artifact store, all 12 core tools, API key auth, and tests — the complete runtime without MCP or UI.

**Branch:** `feature/g1-runtime-core`

**Deliverables:**
- [ ] GitHub repo `github.com/pragnakar/Project_Groot` created
- [ ] `pyproject.toml` — groot-runtime package (fastapi, uvicorn, pydantic, aiosqlite, python-dotenv, mcp)
- [ ] `groot/config.py` — Settings class (GROOT_API_KEYS, GROOT_DB_PATH, GROOT_APPS)
- [ ] `groot/models.py` — Pydantic schemas: BlobResult, BlobMeta, PageResult, PageMeta, SchemaResult, SchemaMeta, LogResult, SystemState, ArtifactSummary
- [ ] `groot/artifact_store.py` — SQLite init + async CRUD for blobs, pages, schemas, events
- [ ] `groot/auth.py` — API key middleware (header + query param)
- [ ] `groot/tools.py` — All 12 core tools + ToolRegistry
- [ ] `groot/server.py` — FastAPI app, lifespan (DB init), tool routes, health check
- [ ] `tests/test_artifact_store.py` — CRUD round-trip tests
- [ ] `tests/test_tools.py` — All 12 tools, happy + error paths
- [ ] `tests/test_auth.py` — Valid key, invalid key, missing key

**Acceptance Criteria:**
- [ ] `pytest tests/` — all tests pass, zero failures
- [ ] `POST /tools/write_blob` → `GET /tools/read_blob` round-trip works end to end
- [ ] `GET /tools/list_blobs` returns correct results with prefix filter
- [ ] `GET /tools/get_system_state` returns uptime, artifact counts
- [ ] Invalid API key returns 401; missing key returns 401; valid key passes
- [ ] All tool responses are Pydantic models — no bare dicts in responses
- [ ] No module-level mutable state anywhere in `groot/`

**Verification Prompt:**
> "Review the Phase G1 implementation against SPEC.md and AGENT.md. Check each acceptance criterion. For each: state PASS or FAIL with specific evidence (test output, line numbers, or observed behaviour). List any items not yet implemented. Do not mark the phase complete until all criteria pass."

---

### Phase G2 — MCP Transport (PLANNED)

**Objective:** Expose all 12 core tools over MCP stdio and SSE transports so Claude Desktop and ChatGPT can call them.

**Branch:** `feature/g2-mcp-transport`

*Spec to be detailed after Phase G1 approval.*

**Key deliverables (stub):**
- `groot/mcp_transport.py` — register all 12 tools as MCP tools
- stdio transport entry point (`__main__.py`)
- SSE transport endpoint
- Verified: Claude Desktop can call `write_blob` and `read_blob` via MCP

---

### Phase G3 — Page Server + React Shell (PLANNED)

**Objective:** Add the dynamic page server and React shell so LLM-registered pages render live at `/apps/:name`.

**Branch:** `feature/g3-page-server`

*Spec to be detailed after Phase G2 approval.*

**Key deliverables (stub):**
- `groot/page_server.py` — dynamic route registration, JSX delivery
- `groot-shell/` — React shell, Babel standalone, built-in dashboard + artifact browser
- Verified: `create_page("test", jsx)` → `/apps/test` renders component
- Tag: `groot-v0.1.0`

---

### Phase G4 — Sage App Module (PLANNED)

**Objective:** Deploy sage-cloud v0.2 as the first Groot app module using sage-solver-core.

**Branch:** `feature/g4-sage-module`

*Spec to be detailed after Phase G3 approval.*

**Key deliverables (stub):**
- `groot-apps/sage/` — tools.py, pages/, loader.py
- 7 sage tools wrapping sage-solver-core (same as sage-mcp, per-request state)
- 3 sage pages: dashboard, result, sensitivity
- Full flow: LLM calls `solve_optimization` → result stored → `/apps/sage-result` renders
- Tags: `groot-v0.1.0` + `sage-v0.2.0`

---

## Data Models

| Entity | Table | Key Fields |
|---|---|---|
| Blob | `blobs` | key (TEXT PK), data (BLOB), content_type, size_bytes, created_at, updated_at |
| Page | `pages` | name (TEXT PK), jsx_code (TEXT), description, created_at, updated_at |
| Schema | `schemas` | name (TEXT PK), schema_json (TEXT), created_at |
| Event | `events` | id (INTEGER PK AUTOINCREMENT), timestamp, level, message, context_json |

Full SQL in `GROOT_SPEC_V0.1.md` section 5.

---

## API Contracts

| Method | Path | Purpose | Phase |
|---|---|---|---|
| GET | `/health` | Health check | G1 |
| POST | `/tools/write_blob` | Write blob to store | G1 |
| GET | `/tools/read_blob` | Read blob by key | G1 |
| GET | `/tools/list_blobs` | List blobs by prefix | G1 |
| DELETE | `/tools/delete_blob` | Delete blob | G1 |
| POST | `/tools/create_page` | Register JSX page | G1 |
| PUT | `/tools/update_page` | Replace page JSX | G1 |
| GET | `/tools/list_pages` | List all pages | G1 |
| DELETE | `/tools/delete_page` | Delete page | G1 |
| POST | `/tools/define_schema` | Store JSON schema | G1 |
| GET | `/tools/get_schema` | Retrieve schema | G1 |
| GET | `/tools/list_schemas` | List all schemas | G1 |
| POST | `/tools/log_event` | Append log entry | G1 |
| GET | `/tools/get_system_state` | Runtime state | G1 |
| GET | `/tools/list_artifacts` | Full inventory | G1 |
| GET | `/api/pages/:name/source` | Serve JSX source | G3 |
| GET | `/` | React shell | G3 |
| GET | `/apps/:name` | Render registered page | G3 |

---

## Open Questions

- [ ] MCP SDK version — confirm latest compatible with FastAPI SSE — *Decision pending G2*
- [ ] sage-solver-core version to pin — confirm v0.1.3 is current — *Decision pending G4*
