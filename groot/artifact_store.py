"""Groot artifact store — SQLite + filesystem persistence for blobs, pages, schemas, and events."""

import json
from datetime import datetime, timezone

import aiosqlite

from groot.models import (
    ArtifactSummary,
    BlobData,
    BlobMeta,
    BlobResult,
    LogResult,
    PageMeta,
    PageResult,
    SchemaMeta,
    SchemaResult,
    SystemState,
)


def _now() -> str:
    """Return current UTC time as ISO 8601 string."""
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


class ArtifactStore:
    """SQLite-backed persistence layer for all Groot artifacts."""

    def __init__(self, db_path: str, artifact_dir: str) -> None:
        self._db_path = db_path
        self._artifact_dir = artifact_dir

    async def init_db(self) -> None:
        """Create all tables if they do not exist."""
        async with aiosqlite.connect(self._db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS blobs (
                    key          TEXT PRIMARY KEY,
                    data         TEXT NOT NULL,
                    content_type TEXT NOT NULL DEFAULT 'text/plain',
                    size_bytes   INTEGER NOT NULL,
                    created_at   TEXT NOT NULL,
                    updated_at   TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS pages (
                    name        TEXT PRIMARY KEY,
                    jsx_code    TEXT NOT NULL,
                    description TEXT NOT NULL DEFAULT '',
                    created_at  TEXT NOT NULL,
                    updated_at  TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS schemas (
                    name        TEXT PRIMARY KEY,
                    schema_json TEXT NOT NULL,
                    created_at  TEXT NOT NULL
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS events (
                    id           INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp    TEXT NOT NULL,
                    level        TEXT NOT NULL DEFAULT 'info',
                    message      TEXT NOT NULL,
                    context_json TEXT NOT NULL DEFAULT '{}'
                )
            """)
            await db.commit()

    # ------------------------------------------------------------------
    # Blob operations
    # ------------------------------------------------------------------

    async def write_blob(self, key: str, data: str, content_type: str = "text/plain") -> BlobResult:
        """Upsert a blob. Sets created_at on insert, updates updated_at always."""
        now = _now()
        size_bytes = len(data.encode("utf-8"))

        async with aiosqlite.connect(self._db_path) as db:
            # Check if exists to preserve created_at
            async with db.execute("SELECT created_at FROM blobs WHERE key = ?", (key,)) as cur:
                row = await cur.fetchone()
            created_at = row[0] if row else now

            await db.execute(
                """
                INSERT INTO blobs (key, data, content_type, size_bytes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    data         = excluded.data,
                    content_type = excluded.content_type,
                    size_bytes   = excluded.size_bytes,
                    updated_at   = excluded.updated_at
                """,
                (key, data, content_type, size_bytes, created_at, now),
            )
            await db.commit()

        return BlobResult(
            key=key,
            size_bytes=size_bytes,
            content_type=content_type,
            created_at=created_at,
            url=f"/blobs/{key}",
        )

    async def read_blob(self, key: str) -> BlobData:
        """Read a blob by key. Raises KeyError if not found."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT key, data, content_type, created_at FROM blobs WHERE key = ?", (key,)
            ) as cur:
                row = await cur.fetchone()

        if row is None:
            raise KeyError(f"Blob not found: {key!r}")

        return BlobData(key=row[0], data=row[1], content_type=row[2], created_at=row[3])

    async def list_blobs(self, prefix: str = "") -> list[BlobMeta]:
        """List blob metadata, optionally filtered by key prefix."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT key, size_bytes, content_type, created_at FROM blobs "
                "WHERE key LIKE ? ORDER BY created_at DESC",
                (f"{prefix}%",),
            ) as cur:
                rows = await cur.fetchall()

        return [BlobMeta(key=r[0], size_bytes=r[1], content_type=r[2], created_at=r[3]) for r in rows]

    async def delete_blob(self, key: str) -> bool:
        """Delete a blob. Returns True if deleted, False if not found."""
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute("DELETE FROM blobs WHERE key = ?", (key,))
            await db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Page operations
    # ------------------------------------------------------------------

    async def create_page(self, name: str, jsx_code: str, description: str = "") -> PageResult:
        """Insert a new page. Raises ValueError if name already exists."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute("SELECT 1 FROM pages WHERE name = ?", (name,)) as cur:
                if await cur.fetchone():
                    raise ValueError(f"Page already exists: {name!r}")
            now = _now()
            await db.execute(
                "INSERT INTO pages (name, jsx_code, description, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (name, jsx_code, description, now, now),
            )
            await db.commit()

        return PageResult(name=name, url=f"/apps/{name}", description=description, created_at=now, updated_at=now)

    async def update_page(self, name: str, jsx_code: str) -> PageResult:
        """Replace a page's JSX. Raises KeyError if not found."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT description, created_at FROM pages WHERE name = ?", (name,)
            ) as cur:
                row = await cur.fetchone()
            if row is None:
                raise KeyError(f"Page not found: {name!r}")
            description, created_at = row[0], row[1]
            now = _now()
            await db.execute(
                "UPDATE pages SET jsx_code = ?, updated_at = ? WHERE name = ?",
                (jsx_code, now, name),
            )
            await db.commit()

        return PageResult(name=name, url=f"/apps/{name}", description=description, created_at=created_at, updated_at=now)

    async def get_page(self, name: str) -> PageResult:
        """Fetch a single page. Raises KeyError if not found."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT name, description, created_at, updated_at FROM pages WHERE name = ?", (name,)
            ) as cur:
                row = await cur.fetchone()

        if row is None:
            raise KeyError(f"Page not found: {name!r}")

        return PageResult(name=row[0], url=f"/apps/{row[0]}", description=row[1], created_at=row[2], updated_at=row[3])

    async def get_page_source(self, name: str) -> str:
        """Fetch raw JSX source for a page. Raises KeyError if not found."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT jsx_code FROM pages WHERE name = ?", (name,)
            ) as cur:
                row = await cur.fetchone()
        if row is None:
            raise KeyError(f"Page not found: {name!r}")
        return row[0]

    async def list_pages(self) -> list[PageMeta]:
        """List all pages sorted by updated_at descending."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT name, description, created_at, updated_at FROM pages ORDER BY updated_at DESC"
            ) as cur:
                rows = await cur.fetchall()

        return [
            PageMeta(name=r[0], url=f"/apps/{r[0]}", description=r[1], created_at=r[2], updated_at=r[3])
            for r in rows
        ]

    async def delete_page(self, name: str) -> bool:
        """Delete a page. Returns True if deleted, False if not found."""
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute("DELETE FROM pages WHERE name = ?", (name,))
            await db.commit()
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Schema operations
    # ------------------------------------------------------------------

    async def define_schema(self, name: str, schema_json: dict) -> SchemaResult:
        """Upsert a named JSON schema."""
        now = _now()
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute("SELECT created_at FROM schemas WHERE name = ?", (name,)) as cur:
                row = await cur.fetchone()
            created_at = row[0] if row else now
            await db.execute(
                """
                INSERT INTO schemas (name, schema_json, created_at)
                VALUES (?, ?, ?)
                ON CONFLICT(name) DO UPDATE SET schema_json = excluded.schema_json
                """,
                (name, json.dumps(schema_json), created_at),
            )
            await db.commit()

        return SchemaResult(name=name, definition=schema_json, created_at=created_at)

    async def get_schema(self, name: str) -> SchemaResult:
        """Fetch a schema by name. Raises KeyError if not found."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT name, schema_json, created_at FROM schemas WHERE name = ?", (name,)
            ) as cur:
                row = await cur.fetchone()

        if row is None:
            raise KeyError(f"Schema not found: {name!r}")

        return SchemaResult(name=row[0], definition=json.loads(row[1]), created_at=row[2])

    async def list_schemas(self) -> list[SchemaMeta]:
        """List all schema metadata."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute("SELECT name, created_at FROM schemas ORDER BY created_at DESC") as cur:
                rows = await cur.fetchall()

        return [SchemaMeta(name=r[0], created_at=r[1]) for r in rows]

    # ------------------------------------------------------------------
    # Event operations
    # ------------------------------------------------------------------

    async def log_event(self, message: str, level: str = "info", context: dict | None = None) -> LogResult:
        """Append a structured log event."""
        if context is None:
            context = {}
        now = _now()
        async with aiosqlite.connect(self._db_path) as db:
            cur = await db.execute(
                "INSERT INTO events (timestamp, level, message, context_json) VALUES (?, ?, ?, ?)",
                (now, level, message, json.dumps(context)),
            )
            row_id = cur.lastrowid
            await db.commit()

        return LogResult(id=row_id, timestamp=now, message=message, level=level)

    async def list_events(self, limit: int = 50) -> list[LogResult]:
        """Return most recent events first."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute(
                "SELECT id, timestamp, message, level FROM events ORDER BY id DESC LIMIT ?", (limit,)
            ) as cur:
                rows = await cur.fetchall()

        return [LogResult(id=r[0], timestamp=r[1], message=r[2], level=r[3]) for r in rows]

    # ------------------------------------------------------------------
    # System operations
    # ------------------------------------------------------------------

    async def get_system_state(self, uptime_seconds: float) -> SystemState:
        """Return runtime state with artifact counts."""
        async with aiosqlite.connect(self._db_path) as db:
            async with db.execute("SELECT COUNT(*) FROM blobs") as cur:
                blob_count = (await cur.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM pages") as cur:
                page_count = (await cur.fetchone())[0]
            async with db.execute("SELECT COUNT(*) FROM schemas") as cur:
                schema_count = (await cur.fetchone())[0]

        return SystemState(
            uptime_seconds=uptime_seconds,
            artifact_count=blob_count + page_count + schema_count,
            page_count=page_count,
            blob_count=blob_count,
            schema_count=schema_count,
        )

    async def list_artifacts(self) -> ArtifactSummary:
        """Return full artifact inventory with last 20 events."""
        pages = await self.list_pages()
        blobs = await self.list_blobs()
        schemas = await self.list_schemas()
        recent_events = await self.list_events(limit=20)

        return ArtifactSummary(pages=pages, blobs=blobs, schemas=schemas, recent_events=recent_events)
