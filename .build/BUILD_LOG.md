# BUILD_LOG.md — Build History
# Project: Project Groot
# Started: 2026-03-13

---

## Log Entry Format

```
[DATE] | [PHASE] | [ACTION]
---
Context: [What state the build was in before this entry]
Work:    [What was done in this session]
Result:  [What changed — files created, decisions made, problems encountered]
Next:    [What comes next — the immediate next action]
Evidence: [Test output, verification results, checksums, or links]
```

---

## Log

2026-03-13 | phase-0 | initialized
---
Context: New project. GROOT_SPEC_V0.1.md and groot_architecture.jsx already authored by claude.ai Cowork instance. ClickUp coordination file in place. Git repo initialized on main branch.
Work:    Bootstrap protocol executed. Read BOOTSTRAP.md, LLM_NATIVE_SOFTWARE_ENGINEERING.md, Testing_Strategy.md. Created .build/ control documents: AGENT.md, SPEC.md, BUILD_LOG.md, spec/schemas/. Derived content from GROOT_SPEC_V0.1.md.
Result:  Project scaffold complete. Phase G1 spec drafted in SPEC.md. AGENT.md captures all constraints, stack, ClickUp protocol, and output conventions.
Next:    Peter reviews SPEC.md Phase G1. claude.ai creates ClickUp tasks in Groot workflow. On Peter's approval (HAND OFF TO CLAUDE CODE), Claude Code begins Phase G1.
Evidence: .build/ directory created with AGENT.md, SPEC.md, BUILD_LOG.md, spec/schemas/. No application code written.

Meta-prompts loaded:
  ✓ LLM-Native Software Engineering (always)
  ✓ API Design (FastAPI REST + MCP tool interface)
  ✓ Database (SQLite artifact store)
  ✓ UI-UX (React shell)
  ✓ Security Engineering (API key middleware)
  ✓ Deployment Engineering (GitHub repo, remote hosts)
  ✓ DevOps (production operation)
  ✓ Testing Strategy (pytest, integration verification)
  ✓ Documentation

---

2026-03-13 | phase-G1 | complete
---
Context: Scaffold initialized. G1 tasks staged in ClickUp Groot workflow list (901113373077) by claude.ai, approved by Peter, handed off to Claude Code.
Work:
  G1-1 (868hw87m7) — Project scaffold, pyproject.toml, groot/config.py, groot/models.py, all stub modules. 31 tests.
  G1-2 (868hw87xp) — groot/artifact_store.py: ArtifactStore class, full async SQLite CRUD for blobs/pages/schemas/events. 24 tests.
  G1-3 (868hw8841) — groot/auth.py: verify_api_key FastAPI dependency, X-Groot-Key header + ?key= query param, dev bypass, production guard. 9 tests.
  G1-4 (868hw88dq) — groot/tools.py: ToolRegistry + 14 core tools + register_core_tools(). Tool metadata (name, description, JSON Schema params) ready for MCP in G2. 22 tests.
  G1-5 (868hw88n2) — groot/server.py: FastAPI lifespan, all HTTP routes under /api/, generic /api/tools/call endpoint, exception handlers, integration tests. 19 tests.
Result:
  Branch: feature/g1-runtime-core @ SHA 79ac953
  Repo: github.com/pragnakar/Project_Groot
  Full suite: 105/105 passed — zero failures, zero warnings
  Phase gate posted: [CLAUDE-CODE] Phase G1 complete (868hw8r3f) → OPEN-HUMAN-REVIEW
Notable fixes:
  - SchemaResult/DefineSchemaRequest: renamed .schema_json/.schema → .definition (Pydantic v2 shadowing)
  - auth.py: Settings injected via Depends(get_settings) not direct call — enables test overrides
  - tools.py: ToolRegistry.call() param renamed name→tool_name to avoid kwarg collision
  - server.py: lifespan reads app.dependency_overrides to respect test settings (temp DB isolation)
  - Spec §4 lists 14 tools (4+4+3+3), not 12 as stated in narrative — implemented all 14
Next: Peter reviews phase gate (868hw8r3f). On approval → G2 (MCP transport: stdio + SSE).
Evidence: pytest 105 passed. All 5 G1 tasks COMPLETE in ClickUp. SHA 79ac953 on remote.

---

2026-03-13 | phase-G2 | complete
---
Context: G1 complete (105 tests). Phase gate (868hw8r3f) approved by Peter. G2 tasks staged in ClickUp by claude.ai, handed off to Claude Code on branch feature/g2-mcp-transport.
Work:
  G2-1 (868hw88wy) — groot/mcp_transport.py: MCPBridge class, register_tools_with_mcp(), run_stdio(). groot/__main__.py: unified entry point (python -m groot, --mcp-stdio, --http). mcp_config.example.json: Claude Desktop config. pyproject.toml: mcp[cli]>=1.26.0 added. 12 tests.
  G2-2 (868hw891x) — mount_sse_transport(): GET /mcp/sse (auth via ?key= query param) + POST /mcp/messages mounted on FastAPI app. server.py lifespan calls mount_sse_transport(). __main__.py: --port flag added. README.md: full quick start. 8 tests.
Result:
  Branch: feature/g2-mcp-transport @ SHA 87a5845 — merged to main
  Repo: github.com/pragnakar/Project_Groot (main is now default branch; feature branches deleted)
  Full suite: 125/125 passed — zero failures, zero warnings
  Phase gate posted: [CLAUDE-CODE] Phase G2 complete (868hw9111) → OPEN-HUMAN-REVIEW
Notable decisions:
  - Used mcp 1.26.0 low-level Server API (not FastMCP) — ToolRegistry schemas flow directly to MCP inputSchema, no duplication
  - MCPBridge is a standalone class: all 12 transport tests use it directly (no JSON-RPC stdio setup needed)
  - SSE routes added via app.router.routes with in-place replacement on each lifespan restart — idempotent for test reuse of module-level FastAPI app
  - SSE auth via ?key= query param only (EventSource API does not support custom headers)
  - SSE streaming path is pragma: no cover in MCP SDK itself; unit tests cover auth + session error responses; full streaming tested end-to-end
  - list/bool tool return values wrapped in {"result": ...} (MCP structured content requires dict)
Next: Peter reviews phase gate (868hw9111). On approval → G3 (page server + React shell).
Evidence: pytest 125 passed. Both G2 tasks COMPLETE in ClickUp. SHA 87a5845 merged to main.

---

2026-03-13 | phase-G3 | complete
---
Context: G2 complete (125 tests). Phase gate (868hw9111) at OPEN-HUMAN-REVIEW. G3 tasks staged in ClickUp by claude.ai, handed off to Claude Code on branch feature/g3-page-server.
Work:
  G3-1 (868hw897m) — groot/page_server.py: PageServer class, _validate_name(), register_static() with upsert pattern, get_routes() returning unauthenticated APIRouter (GET /api/pages, /api/pages/{name}/source, /api/pages/{name}/meta). groot/artifact_store.py: get_page_source() added. server.py lifespan updated: register_builtin_pages, include_router(page_server.get_routes()), idempotent route replacement. 15 tests.
  G3-2 (868hw89bx) — groot-shell/index.html: self-contained React 18 shell using CDN React/ReactDOM + Babel standalone. Hash-based router (#/ → dashboard, #/artifacts → artifact browser, #/apps/{name} → DynamicPage). DynamicPage: fetches /api/pages/{name}/source, Babel-transforms JSX, evals named Page component or wraps bare JSX, 4 error states. ErrorBoundary class component with retry. Dark theme matching groot_architecture.jsx. server.py: SPA catch-all routes (GET /, /artifacts, /apps/{path}) serving index.html via FileResponse. 8 tests.
  G3-3 (868hw89gx) — groot/builtin_pages.py: groot-dashboard JSX (system state stats grid, registered pages list, recent events, quick links) + groot-artifacts JSX (tabs: Blobs/Schemas/Events, inline inspect). register_builtin_pages() upserts both at startup. server.py: calls register_builtin_pages(store) in lifespan. groot-shell/index.html: GrootDashboard and ArtifactBrowser components delegate to DynamicPage. tests/test_g3_integration.py: 12 integration tests covering full create→serve→update→delete cycle. 12 tests.
Result:
  Branch: feature/g3-page-server @ SHA d1ed76c — merged to main
  Tag: groot-v0.1.0 created on main
  Repo: github.com/pragnakar/Project_Groot
  Full suite: 160/160 passed — zero failures, zero warnings
  Groot runtime is functionally complete: HTTP API + MCP stdio + MCP SSE + page server + React shell
Notable decisions:
  - PageServer routes are unauthenticated (GET only, read-only) — shell fetches JSX without a key
  - Built-in pages stored as Python multiline strings in builtin_pages.py, upserted on every lifespan start (handles server restarts cleanly)
  - index.html is fully self-contained (no external App.jsx) — Babel CDN transforms JSX in the browser
  - StaticFiles mount removed: shell has no external assets, catch-all routes (FileResponse) are sufficient and avoid shadowing lifespan-added /api/pages routes
  - DynamicPage supports both named Page components and bare JSX fragments
  - Built-in pages fetch /api/system/state (auth-gated): works in dev bypass mode, gracefully handles 401 in production
Next: Peter reviews G3 output. On approval → G-APP (generalized app module interface).
Evidence: pytest 160 passed. All G3 tasks COMPLETE in ClickUp. SHA d1ed76c merged to main. Tag groot-v0.1.0 pushed to remote.

---

2026-03-13 | phase-G-APP | complete
---
Context: G3 complete (160 tests, groot-v0.1.0 tagged). G-APP task (868hw9808) staged in ClickUp by claude.ai and handed off to Claude Code on branch feature/g-app-interface.
Work:
  G-APP (868hw9808) — Generalized app module interface, discovery API, example scaffold, and developer guide.
    groot/app_interface.py: GrootAppModule Protocol (documentation-first, runtime_checkable, not enforced).
    groot/app_routes.py: unauthenticated GET /api/apps (AppsResponse with core info), GET /api/apps/{name} (AppDetail with tools + pages), GET /api/apps/{name}/health (delegates to module.health_check()).
    groot/models.py: AppInfo, AppDetail, AppHealth, CoreInfo, AppsResponse, ToolInfo models added.
    groot/server.py: lifespan now tracks loaded_apps dict (module, meta, status); register() calls are awaited; app_routes mounted idempotently alongside page_server routes; app.state.loaded_apps persisted.
    groot_apps/_example/: complete reference implementation — echo_tool, EchoResult, hello.jsx static page, APP_META, health_check(). Directory uses _ prefix (Python scaffold convention).
    docs/APP_MODULE_GUIDE.md: self-sufficient developer guide covering contract, tool/page patterns, testing, API reference, FAQ.
    groot/page_server.py: _NAME_RE updated to allow underscores (required for _example-hello page names).
    groot/config.py: GROOT_APPS default updated from 'sage' to '_example'.
    tests/test_app_interface.py: 12 tests — list/detail/health endpoints, namespace isolation, tool callability, graceful degradation for missing modules.
Result:
  Branch: feature/g-app-interface @ SHA a9a5f0a — merged to main @ SHA 22986a5
  Repo: github.com/pragnakar/Project_Groot
  Full suite: 172/172 passed — zero failures, zero warnings
  Groot is now forkable: any developer or AI can copy _example/, implement register(), and integrate in <30 minutes
Notable decisions:
  - Protocol is documentation-only (runtime_checkable but not enforced) — avoids forcing isinstance checks or import overhead on app authors
  - App pages filtered by prefix convention: pages named {app_name}-* belong to that app
  - Namespace isolation verified: _example tools register under '_example' namespace, core tools_count stays at 14
  - ModuleNotFoundError on load = silently skipped (app absent from list); other exceptions = recorded as status:'error'
  - _example directory convention signals "reference scaffold" to developers without polluting the namespace
  - G4 (Sage) deferred to Project Sage repo — will integrate via APP_GUIDE contract as an external module
Next: Project Sage follows APP_MODULE_GUIDE.md contract to integrate as a Groot app module. Groot runtime is complete.
Evidence: pytest 172 passed. Task 868hw9808 COMPLETE in ClickUp. SHA 22986a5 on main (remote).

---

2026-03-13 | post-G-APP | shell-hotfixes — end-to-end MCP verification
---
Context: Groot connected to Claude Desktop via MCP stdio. Live testing revealed three shell rendering issues with LLM-generated JSX.
Work:
  Fix 1 (e99d693) — Strip import/export statements before Babel transform.
    LLM-generated pages include `import React from 'react'` and `export default` which are invalid in the browser eval context. Stripped via regex before transform.
  Fix 2 (0502fb7) — Resolve export default component name when no Page function exists.
    LLM names components after the page (e.g. MyTest, Clock) rather than Page. Capture the exported name from `export default function Name` before stripping, fall back to it if Page is not found.
  Fix 3 (ed91b20) — Inject React hooks as named vars into page eval context.
    LLM-generated JSX uses destructured hooks (useState, useEffect, etc.) directly. Injected all 9 common hooks as named Function parameters alongside React.
Result:
  Full Claude Desktop → MCP stdio → create_page → page server → React shell → browser cycle verified working.
  Live pages tested: animated clock (useState/useEffect/intervals), kanban board (drag-and-drop), data-viz bar chart (CSS animations).
  172 tests still passing. No regressions.
  SHA ed91b20 on main (remote).
Notable:
  - All three issues are inherent to LLM code generation style — unlikely to need further fixes for common patterns
  - Shell now handles: named Page component, export default function AnyName, bare JSX, React.useState style, destructured hook style
