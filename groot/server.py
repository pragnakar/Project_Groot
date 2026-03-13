"""Groot FastAPI application — lifespan, tool routes, health check, app module loader."""

import importlib
import logging
import time
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

_SHELL_DIR = Path(__file__).parent.parent / "groot-shell"

from groot.artifact_store import ArtifactStore
from groot.auth import AuthContext, verify_api_key
from groot.config import Settings, get_settings
from groot.models import (
    ArtifactSummary,
    BlobData,
    BlobMeta,
    BlobResult,
    CreatePageRequest,
    DefineSchemaRequest,
    LogEventRequest,
    LogResult,
    PageMeta,
    PageResult,
    SchemaMeta,
    SchemaResult,
    SystemState,
    ToolError,
    UpdatePageRequest,
    WriteBlobRequest,
)
from groot.builtin_pages import register_builtin_pages
from groot.mcp_transport import mount_sse_transport
from groot.page_server import PageServer
from groot.tools import ToolRegistry, register_core_tools

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Inline request models for simple endpoints
# ---------------------------------------------------------------------------

class ReadBlobRequest(BaseModel):
    key: str


class ListBlobsRequest(BaseModel):
    prefix: str = ""


class DeleteBlobRequest(BaseModel):
    key: str


class DeletePageRequest(BaseModel):
    name: str


class GetSchemaRequest(BaseModel):
    name: str


class ToolCallRequest(BaseModel):
    tool: str
    arguments: dict[str, Any] = {}


# ---------------------------------------------------------------------------
# Lifespan
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Respect dependency_overrides so tests can inject test settings
    settings_fn = app.dependency_overrides.get(get_settings, get_settings)
    settings: Settings = settings_fn()

    store = ArtifactStore(
        db_path=settings.GROOT_DB_PATH,
        artifact_dir=settings.GROOT_ARTIFACT_DIR,
    )
    await store.init_db()

    registry = ToolRegistry()
    register_core_tools(registry, store)

    page_server = PageServer(store)
    await register_builtin_pages(store)

    # Load enabled app modules — graceful skip on missing
    for app_name in settings.apps_list():
        try:
            module = importlib.import_module(f"groot_apps.{app_name}.loader")
            module.register(registry, page_server, store)
            logger.info("Loaded Groot app module: %s", app_name)
        except ModuleNotFoundError:
            logger.warning("Groot app module not found, skipping: %s", app_name)
        except Exception as e:
            logger.warning("Failed to load Groot app module %s: %s", app_name, e)

    # Mount page server routes (idempotent — replaces on each lifespan restart)
    _ps_paths = {"/api/pages", "/api/pages/{name}/source", "/api/pages/{name}/meta"}
    app.router.routes[:] = [r for r in app.router.routes if getattr(r, "path", None) not in _ps_paths]
    app.include_router(page_server.get_routes())

    mount_sse_transport(app, registry, store, settings)

    app.state.store = store
    app.state.registry = registry
    app.state.page_server = page_server
    app.state.start_time = time.time()

    logger.info("Groot runtime started. Apps: %s", settings.apps_list())

    yield

    logger.info("Groot runtime shutting down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title="Groot Runtime",
    version="0.1.0",
    lifespan=lifespan,
)


# ---------------------------------------------------------------------------
# Exception handlers
# ---------------------------------------------------------------------------

@app.exception_handler(KeyError)
async def key_error_handler(request: Request, exc: KeyError):
    return JSONResponse(
        status_code=404,
        content=ToolError(error="not_found", detail=str(exc)).model_dump(),
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=422,
        content=ToolError(error="validation_error", detail=str(exc)).model_dump(),
    )


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

def get_store(request: Request) -> ArtifactStore:
    return request.app.state.store


def get_registry(request: Request) -> ToolRegistry:
    return request.app.state.registry


def get_uptime(request: Request) -> float:
    return time.time() - request.app.state.start_time


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------

@app.get("/health")
async def health():
    return {"status": "ok", "version": "0.1.0"}


# ---------------------------------------------------------------------------
# React shell — SPA routes (must come after API routes so they don't shadow)
# ---------------------------------------------------------------------------

@app.get("/")
async def shell_root():
    return FileResponse(_SHELL_DIR / "index.html")


@app.get("/artifacts")
async def shell_artifacts():
    return FileResponse(_SHELL_DIR / "index.html")


@app.get("/apps/{path:path}")
async def shell_apps(path: str):
    return FileResponse(_SHELL_DIR / "index.html")


# ---------------------------------------------------------------------------
# Tool routes — Storage
# ---------------------------------------------------------------------------

@app.post("/api/tools/write_blob", response_model=BlobResult)
async def write_blob(
    body: WriteBlobRequest,
    store: ArtifactStore = Depends(get_store),
    registry: ToolRegistry = Depends(get_registry),
    auth: AuthContext = Depends(verify_api_key),
):
    result = await registry.call("write_blob", store=store, key=body.key, data=body.data, content_type=body.content_type)
    if isinstance(result, ToolError):
        raise HTTPException(status_code=400, detail=result.model_dump())
    return result


@app.post("/api/tools/read_blob", response_model=BlobData)
async def read_blob(
    body: ReadBlobRequest,
    store: ArtifactStore = Depends(get_store),
    registry: ToolRegistry = Depends(get_registry),
    auth: AuthContext = Depends(verify_api_key),
):
    result = await registry.call("read_blob", store=store, key=body.key)
    if isinstance(result, ToolError):
        raise HTTPException(status_code=400, detail=result.model_dump())
    return result


@app.post("/api/tools/list_blobs")
async def list_blobs(
    body: ListBlobsRequest = ListBlobsRequest(),
    store: ArtifactStore = Depends(get_store),
    registry: ToolRegistry = Depends(get_registry),
    auth: AuthContext = Depends(verify_api_key),
) -> list[BlobMeta]:
    return await registry.call("list_blobs", store=store, prefix=body.prefix)


@app.post("/api/tools/delete_blob")
async def delete_blob(
    body: DeleteBlobRequest,
    store: ArtifactStore = Depends(get_store),
    registry: ToolRegistry = Depends(get_registry),
    auth: AuthContext = Depends(verify_api_key),
):
    result = await registry.call("delete_blob", store=store, key=body.key)
    return {"deleted": result}


# ---------------------------------------------------------------------------
# Tool routes — Pages
# ---------------------------------------------------------------------------

@app.post("/api/tools/create_page", response_model=PageResult)
async def create_page(
    body: CreatePageRequest,
    store: ArtifactStore = Depends(get_store),
    registry: ToolRegistry = Depends(get_registry),
    auth: AuthContext = Depends(verify_api_key),
):
    result = await registry.call("create_page", store=store, name=body.name, jsx_code=body.jsx_code, description=body.description)
    if isinstance(result, ToolError):
        raise HTTPException(status_code=400, detail=result.model_dump())
    return result


@app.post("/api/tools/update_page", response_model=PageResult)
async def update_page(
    body: UpdatePageRequest,
    store: ArtifactStore = Depends(get_store),
    registry: ToolRegistry = Depends(get_registry),
    auth: AuthContext = Depends(verify_api_key),
):
    result = await registry.call("update_page", store=store, name=body.name, jsx_code=body.jsx_code)
    if isinstance(result, ToolError):
        raise HTTPException(status_code=400, detail=result.model_dump())
    return result


@app.post("/api/tools/list_pages")
async def list_pages(
    store: ArtifactStore = Depends(get_store),
    registry: ToolRegistry = Depends(get_registry),
    auth: AuthContext = Depends(verify_api_key),
) -> list[PageMeta]:
    return await registry.call("list_pages", store=store)


@app.post("/api/tools/delete_page")
async def delete_page(
    body: DeletePageRequest,
    store: ArtifactStore = Depends(get_store),
    registry: ToolRegistry = Depends(get_registry),
    auth: AuthContext = Depends(verify_api_key),
):
    result = await registry.call("delete_page", store=store, name=body.name)
    return {"deleted": result}


# ---------------------------------------------------------------------------
# Tool routes — Schemas
# ---------------------------------------------------------------------------

@app.post("/api/tools/define_schema", response_model=SchemaResult)
async def define_schema(
    body: DefineSchemaRequest,
    store: ArtifactStore = Depends(get_store),
    registry: ToolRegistry = Depends(get_registry),
    auth: AuthContext = Depends(verify_api_key),
):
    result = await registry.call("define_schema", store=store, name=body.name, schema=body.definition)
    if isinstance(result, ToolError):
        raise HTTPException(status_code=400, detail=result.model_dump())
    return result


@app.post("/api/tools/get_schema", response_model=SchemaResult)
async def get_schema(
    body: GetSchemaRequest,
    store: ArtifactStore = Depends(get_store),
    registry: ToolRegistry = Depends(get_registry),
    auth: AuthContext = Depends(verify_api_key),
):
    result = await registry.call("get_schema", store=store, name=body.name)
    if isinstance(result, ToolError):
        raise HTTPException(status_code=400, detail=result.model_dump())
    return result


@app.post("/api/tools/list_schemas")
async def list_schemas(
    store: ArtifactStore = Depends(get_store),
    registry: ToolRegistry = Depends(get_registry),
    auth: AuthContext = Depends(verify_api_key),
) -> list[SchemaMeta]:
    return await registry.call("list_schemas", store=store)


# ---------------------------------------------------------------------------
# Tool routes — System
# ---------------------------------------------------------------------------

@app.post("/api/tools/log_event", response_model=LogResult)
async def log_event(
    body: LogEventRequest,
    store: ArtifactStore = Depends(get_store),
    registry: ToolRegistry = Depends(get_registry),
    auth: AuthContext = Depends(verify_api_key),
):
    return await registry.call("log_event", store=store, message=body.message, level=body.level, context=body.context)


@app.get("/api/system/state", response_model=SystemState)
async def system_state(
    request: Request,
    store: ArtifactStore = Depends(get_store),
    registry: ToolRegistry = Depends(get_registry),
    auth: AuthContext = Depends(verify_api_key),
):
    uptime = get_uptime(request)
    return await registry.call("get_system_state", store=store, uptime_seconds=uptime)


@app.get("/api/system/artifacts", response_model=ArtifactSummary)
async def system_artifacts(
    store: ArtifactStore = Depends(get_store),
    registry: ToolRegistry = Depends(get_registry),
    auth: AuthContext = Depends(verify_api_key),
):
    return await registry.call("list_artifacts", store=store)


# ---------------------------------------------------------------------------
# Generic tool call endpoint (MCP-to-HTTP bridge for G2)
# ---------------------------------------------------------------------------

@app.post("/api/tools/call")
async def tool_call(
    body: ToolCallRequest,
    store: ArtifactStore = Depends(get_store),
    registry: ToolRegistry = Depends(get_registry),
    auth: AuthContext = Depends(verify_api_key),
):
    result = await registry.call(body.tool, store=store, **body.arguments)
    if isinstance(result, ToolError):
        raise HTTPException(status_code=400, detail=result.model_dump())
    # Return serializable result
    if hasattr(result, "model_dump"):
        return result.model_dump()
    return result


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    import uvicorn
    settings = get_settings()
    uvicorn.run("groot.server:app", host=settings.GROOT_HOST, port=settings.GROOT_PORT, reload=True)
