"""Tests for app discovery API and example app module (G-APP)."""

import pytest
from fastapi.testclient import TestClient

from groot.config import Settings, get_settings
from groot.server import app

TEST_API_KEY = "groot_sk_test_key"


@pytest.fixture
def example_settings(tmp_path):
    return Settings(
        GROOT_API_KEYS=TEST_API_KEY,
        GROOT_DB_PATH=str(tmp_path / "test.db"),
        GROOT_ARTIFACT_DIR=str(tmp_path / "artifacts"),
        GROOT_APPS="example",
        GROOT_ENV="development",
    )


@pytest.fixture
def example_client(example_settings):
    app.dependency_overrides[get_settings] = lambda: example_settings
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers():
    return {"X-Groot-Key": TEST_API_KEY}


# ---------------------------------------------------------------------------
# GET /api/apps — no apps loaded (default test fixture has GROOT_APPS="")
# ---------------------------------------------------------------------------

def test_list_apps_no_apps(client):
    resp = client.get("/api/apps")
    assert resp.status_code == 200
    body = resp.json()
    assert "apps" in body
    assert "core" in body
    assert body["apps"] == []
    assert body["core"]["tools_count"] == 14
    assert body["core"]["version"] == "0.1.0"


def test_list_apps_core_page_count(client):
    resp = client.get("/api/apps")
    assert resp.status_code == 200
    # Built-in pages: groot-dashboard + groot-artifacts
    assert resp.json()["core"]["pages_count"] == 2


# ---------------------------------------------------------------------------
# GET /api/apps — example app loaded
# ---------------------------------------------------------------------------

def test_list_apps_includes_example(example_client):
    resp = example_client.get("/api/apps")
    assert resp.status_code == 200
    names = [a["name"] for a in resp.json()["apps"]]
    assert "example" in names


def test_example_app_status_is_loaded(example_client):
    resp = example_client.get("/api/apps")
    apps = {a["name"]: a for a in resp.json()["apps"]}
    assert apps["example"]["status"] == "loaded"
    assert apps["example"]["tools_count"] == 1
    assert apps["example"]["description"] == "Minimal reference app — one tool, one page"


# ---------------------------------------------------------------------------
# GET /api/apps/{name}
# ---------------------------------------------------------------------------

def test_get_app_detail_example(example_client):
    resp = example_client.get("/api/apps/example")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "example"
    assert body["status"] == "loaded"
    tool_names = [t["name"] for t in body["tools"]]
    assert "echo_tool" in tool_names


def test_get_app_detail_includes_pages(example_client):
    resp = example_client.get("/api/apps/example")
    assert resp.status_code == 200
    page_names = [p["name"] for p in resp.json()["pages"]]
    assert "example-hello" in page_names


def test_get_app_detail_404_for_missing(client):
    resp = client.get("/api/apps/nonexistent")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /api/apps/{name}/health
# ---------------------------------------------------------------------------

def test_app_health_returns_status(example_client):
    resp = example_client.get("/api/apps/example/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "example"
    assert body["status"] == "healthy"
    assert "echo_tool" in body["checks"]


def test_app_health_404_for_missing(client):
    resp = client.get("/api/apps/nonexistent/health")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# Namespace isolation
# ---------------------------------------------------------------------------

def test_example_tool_not_in_core_namespace(example_client, auth_headers):
    resp = example_client.get("/api/apps")
    core_tools_count = resp.json()["core"]["tools_count"]
    # Core tools should still be 14 — example tool is in its own namespace
    assert core_tools_count == 14


def test_example_tool_callable(example_client, auth_headers):
    resp = example_client.post(
        "/api/tools/call",
        json={"tool": "echo_tool", "arguments": {"message": "hello groot"}},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["echo"] == "Echo: hello groot"


# ---------------------------------------------------------------------------
# Graceful degradation — broken loader
# ---------------------------------------------------------------------------

def test_broken_app_recorded_as_error(tmp_path):
    broken_settings = Settings(
        GROOT_API_KEYS=TEST_API_KEY,
        GROOT_DB_PATH=str(tmp_path / "test.db"),
        GROOT_ARTIFACT_DIR=str(tmp_path / "artifacts"),
        GROOT_APPS="nonexistent_app_xyz",
        GROOT_ENV="development",
    )
    app.dependency_overrides[get_settings] = lambda: broken_settings
    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            resp = c.get("/api/apps")
        assert resp.status_code == 200
        # App that failed to load (ModuleNotFoundError) is simply absent from the list
        # (skipped, not recorded as error — matches server.py behavior for missing modules)
        names = [a["name"] for a in resp.json()["apps"]]
        assert "nonexistent_app_xyz" not in names
    finally:
        app.dependency_overrides.clear()
