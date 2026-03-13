# Project Groot

Domain-agnostic LLM runtime environment.

Groot gives any MCP-compatible LLM agent a persistent execution layer: a SQLite artifact store, a validated tool interface (12 core tools), a React page server, and a pluggable domain module system. The LLM is always external — Groot never embeds a model.

**Phase G1 in progress.**

---

## Quick start

```bash
cp .env.example .env
pip install -e ".[dev]"
uvicorn groot.server:app --reload
```

## Architecture

See `GROOT_SPEC_V0.1.md` for full spec and `groot_architecture.jsx` for the architecture diagram.

## Build phases

| Phase | Description | Status |
|---|---|---|
| G1 | Runtime core: FastAPI + SQLite + 12 tools + auth | In progress |
| G2 | MCP transport: stdio + SSE | Planned |
| G3 | Page server + React shell | Planned |
| G4 | sage/ app module (sage-cloud v0.2) | Planned |
