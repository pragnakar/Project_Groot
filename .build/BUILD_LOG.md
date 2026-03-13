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
