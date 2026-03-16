"""Groot app discovery routes — GET /api/apps, /api/apps/{name}, /api/apps/{name}/health, DELETE /api/apps/{name}, GET /api/apps/{name}/export."""

import io
import json
import logging
import shutil
import zipfile
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from groot.auth import AuthContext, verify_api_key
from groot.models import AppDeleteResult, AppDetail, AppHealth, AppInfo, AppsResponse, CoreInfo, PageMeta, ToolInfo

_GROOT_APPS_DIR = Path(__file__).parent.parent / "groot_apps"

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

    @router.delete("/api/apps/{name}", response_model=AppDeleteResult)
    async def delete_app(
        name: str,
        request: Request,
        purge_data: bool = Query(default=False),
        force: bool = Query(default=False),
        auth: AuthContext = Depends(verify_api_key),
    ):
        """Unregister an app module and remove its pages. Requires auth.

        - purge_data=true: also delete blobs and schemas prefixed with the app name
        - force=true: required to delete a currently-loaded (running) app and remove its directory
        """
        loaded_apps: dict = getattr(request.app.state, "loaded_apps", {})
        if name not in loaded_apps:
            raise HTTPException(status_code=404, detail=f"App not found: {name!r}")

        entry = loaded_apps[name]
        status = entry.get("status", "error")

        # Protection: loaded apps require force=true
        if status == "loaded" and not force:
            raise HTTPException(
                status_code=409,
                detail=f"App {name!r} is currently loaded. Use ?force=true to delete it.",
            )

        registry = request.app.state.registry
        store = request.app.state.store

        # 1. Unregister tools
        tools_removed = registry.unregister_namespace(name)

        # 2. Remove app pages (pages prefixed with "{name}-")
        all_pages = await store.list_pages()
        app_pages = [p.name for p in all_pages if p.name.startswith(f"{name}-")]
        for page_name in app_pages:
            await store.delete_page(page_name)

        # 3. Purge blobs and schemas if requested
        blobs_removed = 0
        schemas_removed = 0
        if purge_data:
            app_blobs = await store.list_blobs(prefix=f"{name}/")
            for blob in app_blobs:
                await store.delete_blob(blob.key)
                blobs_removed += 1

            all_schemas = await store.list_schemas()
            for schema in all_schemas:
                if schema.name.startswith(f"{name}/") or schema.name.startswith(f"{name}-"):
                    # ArtifactStore has no delete_schema — skip silently if absent
                    if hasattr(store, "delete_schema"):
                        await store.delete_schema(schema.name)
                        schemas_removed += 1

        # 4. Remove from loaded_apps registry
        del loaded_apps[name]

        # 5. Remove app directory from groot_apps/ (only with force)
        directory_removed = False
        if force:
            app_dir = _GROOT_APPS_DIR / name
            if app_dir.exists() and app_dir.is_dir():
                shutil.rmtree(app_dir)
                directory_removed = True
                logger.info("Removed app directory: %s", app_dir)

        logger.info("Deleted app %r: tools=%d pages=%d blobs=%d schemas=%d dir=%s",
                    name, tools_removed, len(app_pages), blobs_removed, schemas_removed, directory_removed)

        return AppDeleteResult(
            name=name,
            tools_removed=tools_removed,
            pages_removed=len(app_pages),
            blobs_removed=blobs_removed,
            schemas_removed=schemas_removed,
            directory_removed=directory_removed,
        )

    @router.get("/api/apps/{name}/export")
    async def export_app(
        name: str,
        request: Request,
        include_data: bool = Query(default=False),
    ):
        """Export app module as a downloadable .zip archive.

        Packages groot_apps/{name}/ into a ZIP. With ?include_data=true,
        also bundles the app's registered pages and blobs as JSON files.
        """
        loaded_apps: dict = getattr(request.app.state, "loaded_apps", {})
        if name not in loaded_apps:
            raise HTTPException(status_code=404, detail=f"App not found: {name!r}")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            # 1. Package the module directory
            app_dir = _GROOT_APPS_DIR / name
            if app_dir.exists() and app_dir.is_dir():
                for file_path in app_dir.rglob("*"):
                    if file_path.is_file() and "__pycache__" not in file_path.parts:
                        arcname = Path(name) / file_path.relative_to(app_dir)
                        zf.write(file_path, arcname)
            else:
                logger.warning("Export: app directory not found on disk for %r", name)

            # 2. Write app metadata as JSON
            entry = loaded_apps[name]
            meta = {
                "name": name,
                "status": entry.get("status"),
                "meta": entry.get("meta", {}),
            }
            zf.writestr(f"{name}/_export_meta.json", json.dumps(meta, indent=2))

            # 3. Optionally bundle pages and blobs
            if include_data:
                store = request.app.state.store
                all_pages = await store.list_pages()
                app_pages = [p for p in all_pages if p.name.startswith(f"{name}-")]
                pages_export = []
                for page_meta in app_pages:
                    try:
                        source = await store.get_page_source(page_meta.name)
                        pages_export.append({"name": page_meta.name, "source": source})
                    except Exception:
                        pass
                if pages_export:
                    zf.writestr(f"{name}/_export_pages.json", json.dumps(pages_export, indent=2))

                app_blobs = await store.list_blobs(prefix=f"{name}/")
                blobs_export = []
                for blob_meta in app_blobs:
                    try:
                        blob_data = await store.read_blob(blob_meta.key)
                        blobs_export.append({
                            "key": blob_meta.key,
                            "data": blob_data.data,
                            "content_type": blob_meta.content_type,
                        })
                    except Exception:
                        pass
                if blobs_export:
                    zf.writestr(f"{name}/_export_blobs.json", json.dumps(blobs_export, indent=2))

        buf.seek(0)
        filename = f"{name}.zip"
        return StreamingResponse(
            buf,
            media_type="application/zip",
            headers={"Content-Disposition": f"attachment; filename={filename}"},
        )

    return router
