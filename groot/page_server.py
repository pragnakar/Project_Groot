"""Groot page server — dynamic route registration and JSX source delivery."""

import logging
import re
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import PlainTextResponse

from groot.artifact_store import ArtifactStore
from groot.models import PageMeta, PageResult

logger = logging.getLogger(__name__)

# Page names: start with alphanumeric or underscore, then alphanumeric, hyphens, or underscores
_NAME_RE = re.compile(r"^[a-zA-Z0-9_][a-zA-Z0-9_\-]*$")


def _validate_name(name: str) -> None:
    """Raise ValueError if name is not URL-safe (alphanumeric, hyphens, underscores)."""
    if not _NAME_RE.match(name):
        raise ValueError(
            f"Page name must contain only alphanumeric characters and hyphens: {name!r}"
        )


class PageServer:
    """Serves JSX pages from the artifact store and handles static app-module registration."""

    def __init__(self, store: ArtifactStore) -> None:
        self.store = store

    async def register_static(self, name: str, jsx_path: str, app_name: str = "") -> None:
        """Register a static JSX file from an app module's pages/ directory.

        Reads the file at jsx_path and upserts it into the artifact store.
        If app_name is provided, prefixes the page name: {app_name}-{name}.
        """
        full_name = f"{app_name}-{name}" if app_name else name
        _validate_name(full_name)
        jsx_code = Path(jsx_path).read_text(encoding="utf-8")
        try:
            await self.store.create_page(full_name, jsx_code)
        except ValueError:
            # Page already exists — update JSX to latest
            await self.store.update_page(full_name, jsx_code)
        logger.info("Registered static page: %s from %s", full_name, jsx_path)

    def get_routes(self) -> APIRouter:
        """Return a router with all page-serving endpoints (no auth required)."""
        router = APIRouter()
        store = self.store

        @router.get("/api/pages", response_model=list[PageMeta])
        async def list_pages():
            """List all registered pages."""
            return await store.list_pages()

        @router.get("/api/pages/{name}/source", response_class=PlainTextResponse)
        async def page_source(name: str):
            """Return raw JSX source as text/plain (for client-side Babel transform)."""
            try:
                jsx = await store.get_page_source(name)
            except KeyError:
                raise HTTPException(status_code=404, detail=f"Page not found: {name!r}")
            return PlainTextResponse(jsx, media_type="text/plain")

        @router.get("/api/pages/{name}/meta", response_model=PageResult)
        async def page_meta(name: str):
            """Return page metadata (name, description, timestamps)."""
            try:
                return await store.get_page(name)
            except KeyError:
                raise HTTPException(status_code=404, detail=f"Page not found: {name!r}")

        return router
