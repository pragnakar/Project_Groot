"""Groot Runtime entry point.

Usage:
  python -m groot                    # Start HTTP server (uvicorn)
  python -m groot --mcp-stdio        # Start MCP stdio transport
  python -m groot --mcp-stdio --http # Both (HTTP in background, stdio in foreground)
"""

import argparse
import asyncio
import importlib
import logging

logger = logging.getLogger(__name__)


async def _build_runtime():
    """Initialize ArtifactStore + ToolRegistry. Shared across transports."""
    from groot.artifact_store import ArtifactStore
    from groot.config import get_settings
    from groot.tools import ToolRegistry, register_core_tools

    settings = get_settings()
    store = ArtifactStore(
        db_path=settings.GROOT_DB_PATH,
        artifact_dir=settings.GROOT_ARTIFACT_DIR,
    )
    await store.init_db()

    registry = ToolRegistry()
    register_core_tools(registry, store)

    for app_name in settings.apps_list():
        try:
            module = importlib.import_module(f"groot_apps.{app_name}.loader")
            module.register(registry, store)
            logger.info("Loaded app module: %s", app_name)
        except ModuleNotFoundError:
            logger.warning("App module not found, skipping: %s", app_name)
        except Exception as e:
            logger.warning("Failed to load app module %s: %s", app_name, e)

    return store, registry


def main():
    parser = argparse.ArgumentParser(description="Groot Runtime")
    parser.add_argument("--mcp-stdio", action="store_true", help="Start MCP stdio transport")
    parser.add_argument(
        "--http",
        action="store_true",
        help="Start HTTP server in background thread (only valid with --mcp-stdio)",
    )
    args = parser.parse_args()

    if args.mcp_stdio:
        if args.http:
            import threading
            from groot.config import get_settings
            settings = get_settings()

            def _run_http():
                import uvicorn
                uvicorn.run("groot.server:app", host=settings.GROOT_HOST, port=settings.GROOT_PORT)

            t = threading.Thread(target=_run_http, daemon=True)
            t.start()

        async def _run_stdio():
            from groot.mcp_transport import run_stdio
            store, registry = await _build_runtime()
            await run_stdio(store, registry)

        asyncio.run(_run_stdio())
    else:
        import uvicorn
        from groot.config import get_settings
        settings = get_settings()
        uvicorn.run(
            "groot.server:app",
            host=settings.GROOT_HOST,
            port=settings.GROOT_PORT,
            reload=True,
        )


if __name__ == "__main__":
    main()
