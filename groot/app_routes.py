"""Groot app discovery routes — GET /api/apps, /api/apps/{name}, /api/apps/{name}/health."""

import logging

from fastapi import APIRouter, HTTPException, Request

from groot.models import AppDetail, AppHealth, AppInfo, AppsResponse, CoreInfo, PageMeta, ToolInfo

logger = logging.getLogger(__name__)

_CORE_VERSION = "0.1.0"
_BUILTIN_PAGES = {"groot-dashboard", "groot-artifacts"}


def get_app_routes() -> APIRouter:
    """Return a router with all unauthenticated app discovery endpoints."""
    router = APIRouter()

    @router.get("/api/apps", response_model=AppsResponse)
    async def list_apps(request: Request):
        """List all loaded app modules with tool/page counts, plus core runtime summary."""
        registry = request.app.state.registry
        store = request.app.state.store
        loaded_apps: dict = getattr(request.app.state, "loaded_apps", {})

        all_pages = await store.list_pages()
        core_page_count = sum(1 for p in all_pages if p.name in _BUILTIN_PAGES)
        core_tools = registry.list_tools(namespace="core")

        app_infos = []
        for name, entry in loaded_apps.items():
            meta = entry.get("meta", {})
            status = entry.get("status", "error")
            app_tools = registry.list_tools(namespace=name) if status == "loaded" else []
            app_pages = [p for p in all_pages if p.name.startswith(f"{name}-")]
            app_infos.append(AppInfo(
                name=name,
                namespace=name,
                tools_count=len(app_tools),
                pages_count=len(app_pages),
                status=status,
                description=meta.get("description", ""),
            ))

        return AppsResponse(
            apps=app_infos,
            core=CoreInfo(
                tools_count=len(core_tools),
                pages_count=core_page_count,
                version=_CORE_VERSION,
            ),
        )

    @router.get("/api/apps/{name}", response_model=AppDetail)
    async def get_app(name: str, request: Request):
        """Return full detail for a loaded app: tools with schemas, registered pages."""
        loaded_apps: dict = getattr(request.app.state, "loaded_apps", {})
        if name not in loaded_apps:
            raise HTTPException(status_code=404, detail=f"App not found: {name!r}")

        entry = loaded_apps[name]
        status = entry.get("status", "error")
        registry = request.app.state.registry
        store = request.app.state.store

        app_tools = []
        app_pages: list[PageMeta] = []

        if status == "loaded":
            app_tools = [
                ToolInfo(name=t.name, description=t.description, parameters=t.parameters)
                for t in registry.list_tools(namespace=name)
            ]
            all_pages = await store.list_pages()
            app_pages = [p for p in all_pages if p.name.startswith(f"{name}-")]

        return AppDetail(
            name=name,
            namespace=name,
            tools=app_tools,
            pages=app_pages,
            status=status,
        )

    @router.get("/api/apps/{name}/health", response_model=AppHealth)
    async def app_health(name: str, request: Request):
        """Call the app's health_check() if it provides one, else return basic status."""
        loaded_apps: dict = getattr(request.app.state, "loaded_apps", {})
        if name not in loaded_apps:
            raise HTTPException(status_code=404, detail=f"App not found: {name!r}")

        entry = loaded_apps[name]
        status = entry.get("status", "error")

        if status != "loaded":
            return AppHealth(name=name, status="error", checks={"error": entry.get("error", "load failed")})

        module = entry.get("module")
        health_fn = getattr(module, "health_check", None)
        if health_fn is None:
            return AppHealth(name=name, status="healthy", checks={})

        try:
            result = await health_fn()
            return AppHealth(
                name=name,
                status=result.get("status", "healthy"),
                checks=result.get("checks", {}),
            )
        except Exception as e:
            logger.warning("health_check() for app %r raised: %s", name, e)
            return AppHealth(name=name, status="error", checks={"exception": str(e)})

    return router
