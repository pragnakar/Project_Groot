"""Pydantic v2 models for all Groot core tool I/O."""

from typing import Any, Callable

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# Storage models
# ---------------------------------------------------------------------------

class BlobResult(BaseModel):
    """Response for write_blob."""
    key: str
    size_bytes: int
    content_type: str
    created_at: str  # ISO 8601 UTC
    url: str


class BlobData(BaseModel):
    """Response for read_blob."""
    key: str
    data: str  # base64-encoded for binary; raw for text
    content_type: str
    created_at: str  # ISO 8601 UTC


class BlobMeta(BaseModel):
    """Single entry in list_blobs response."""
    key: str
    size_bytes: int
    content_type: str
    created_at: str  # ISO 8601 UTC


# ---------------------------------------------------------------------------
# Page models
# ---------------------------------------------------------------------------

class PageResult(BaseModel):
    """Response for create_page / update_page."""
    name: str
    url: str
    description: str = ""
    created_at: str  # ISO 8601 UTC
    updated_at: str  # ISO 8601 UTC


class PageMeta(BaseModel):
    """Single entry in list_pages response."""
    name: str
    url: str
    description: str = ""
    created_at: str  # ISO 8601 UTC
    updated_at: str  # ISO 8601 UTC


# ---------------------------------------------------------------------------
# Schema models
# ---------------------------------------------------------------------------

class SchemaResult(BaseModel):
    """Response for define_schema / get_schema."""
    name: str
    definition: dict[str, Any]  # the JSON schema content
    created_at: str  # ISO 8601 UTC


class SchemaMeta(BaseModel):
    """Single entry in list_schemas response."""
    name: str
    created_at: str  # ISO 8601 UTC


# ---------------------------------------------------------------------------
# System models
# ---------------------------------------------------------------------------

class LogResult(BaseModel):
    """Response for log_event."""
    id: int
    timestamp: str  # ISO 8601 UTC
    message: str
    level: str = "info"


class SystemState(BaseModel):
    """Response for get_system_state."""
    uptime_seconds: float
    artifact_count: int
    page_count: int
    blob_count: int
    schema_count: int
    registered_apps: list[str] = Field(default_factory=list)


class ArtifactSummary(BaseModel):
    """Response for list_artifacts."""
    pages: list[PageMeta] = Field(default_factory=list)
    blobs: list[BlobMeta] = Field(default_factory=list)
    schemas: list[SchemaMeta] = Field(default_factory=list)
    recent_events: list[LogResult] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Error model
# ---------------------------------------------------------------------------

class ToolError(BaseModel):
    """Structured error returned by all tool failures."""
    error: str
    detail: str = ""
    tool_name: str = ""


# ---------------------------------------------------------------------------
# Tool registry models
# ---------------------------------------------------------------------------

class ToolDefinition(BaseModel):
    """Metadata for a registered tool — used for MCP registration and introspection."""
    model_config = ConfigDict(arbitrary_types_allowed=True)

    name: str
    description: str
    namespace: str = "core"
    parameters: dict[str, Any] = Field(default_factory=dict)
    fn: Callable = Field(exclude=True)  # excluded from serialization


# ---------------------------------------------------------------------------
# Request models (HTTP routes)
# ---------------------------------------------------------------------------

class WriteBlobRequest(BaseModel):
    key: str
    data: str
    content_type: str = "text/plain"


class CreatePageRequest(BaseModel):
    name: str
    jsx_code: str
    description: str = ""


class UpdatePageRequest(BaseModel):
    name: str
    jsx_code: str


class DefineSchemaRequest(BaseModel):
    name: str
    definition: dict[str, Any]  # the JSON schema to store


class LogEventRequest(BaseModel):
    message: str
    level: str = "info"
    context: dict[str, Any] = Field(default_factory=dict)
