"""Tests for groot/page_server.py — PageServer routes and static registration."""

import os
import tempfile
from pathlib import Path

import pytest

from groot.artifact_store import ArtifactStore
from groot.page_server import PageServer, _validate_name


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
async def ps():
    """Standalone PageServer backed by a temp ArtifactStore."""
    with tempfile.TemporaryDirectory() as tmpdir:
        store = ArtifactStore(db_path=os.path.join(tmpdir, "t.db"), artifact_dir=tmpdir)
        await store.init_db()
        yield PageServer(store)


# ---------------------------------------------------------------------------
# Name validation
# ---------------------------------------------------------------------------

def test_valid_names_pass():
    for name in ("dashboard", "my-page", "sage-result", "Page1", "a"):
        _validate_name(name)  # must not raise


def test_invalid_names_raise():
    for name in ("-bad", "has space", "under_score", "", "dot.name"):
        with pytest.raises(ValueError):
            _validate_name(name)


# ---------------------------------------------------------------------------
# GET /api/pages — list
# ---------------------------------------------------------------------------

def test_list_pages_empty(client, auth_headers):
    resp = client.get("/api/pages")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_pages_after_create(client, auth_headers):
    client.post(
        "/api/tools/create_page",
        json={"name": "my-page", "jsx_code": "<div/>", "description": "test"},
        headers=auth_headers,
    )
    resp = client.get("/api/pages")
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert "my-page" in names


def test_list_pages_multiple(client, auth_headers):
    for name in ("alpha", "beta", "gamma"):
        client.post(
            "/api/tools/create_page",
            json={"name": name, "jsx_code": f"<div>{name}</div>"},
            headers=auth_headers,
        )
    resp = client.get("/api/pages")
    assert resp.status_code == 200
    names = [p["name"] for p in resp.json()]
    assert "alpha" in names
    assert "beta" in names
    assert "gamma" in names


# ---------------------------------------------------------------------------
# GET /api/pages/{name}/source
# ---------------------------------------------------------------------------

def test_page_source_returns_jsx(client, auth_headers):
    client.post(
        "/api/tools/create_page",
        json={"name": "src-test", "jsx_code": "<h1>Hello Groot</h1>"},
        headers=auth_headers,
    )
    resp = client.get("/api/pages/src-test/source")
    assert resp.status_code == 200
    assert resp.text == "<h1>Hello Groot</h1>"


def test_page_source_content_type_is_text_plain(client, auth_headers):
    client.post(
        "/api/tools/create_page",
        json={"name": "ct-test", "jsx_code": "<span/>"},
        headers=auth_headers,
    )
    resp = client.get("/api/pages/ct-test/source")
    assert resp.status_code == 200
    assert resp.headers["content-type"].startswith("text/plain")


def test_page_source_404_for_missing(client):
    resp = client.get("/api/pages/nonexistent/source")
    assert resp.status_code == 404


def test_page_source_after_update(client, auth_headers):
    client.post(
        "/api/tools/create_page",
        json={"name": "upd-test", "jsx_code": "<div>old</div>"},
        headers=auth_headers,
    )
    client.post(
        "/api/tools/update_page",
        json={"name": "upd-test", "jsx_code": "<div>new</div>"},
        headers=auth_headers,
    )
    resp = client.get("/api/pages/upd-test/source")
    assert resp.status_code == 200
    assert resp.text == "<div>new</div>"


# ---------------------------------------------------------------------------
# GET /api/pages/{name}/meta
# ---------------------------------------------------------------------------

def test_page_meta_returns_metadata(client, auth_headers):
    client.post(
        "/api/tools/create_page",
        json={"name": "meta-test", "jsx_code": "<div/>", "description": "my desc"},
        headers=auth_headers,
    )
    resp = client.get("/api/pages/meta-test/meta")
    assert resp.status_code == 200
    body = resp.json()
    assert body["name"] == "meta-test"
    assert body["description"] == "my desc"
    assert "created_at" in body
    assert "updated_at" in body


def test_page_meta_404_for_missing(client):
    resp = client.get("/api/pages/ghost/meta")
    assert resp.status_code == 404


# ---------------------------------------------------------------------------
# register_static
# ---------------------------------------------------------------------------

async def test_register_static_stores_jsx(ps):
    with tempfile.NamedTemporaryFile(suffix=".jsx", mode="w", delete=False) as f:
        f.write("<div>Static Page</div>")
        jsx_path = f.name
    try:
        await ps.register_static("home", jsx_path)
        source = await ps.store.get_page_source("home")
        assert source == "<div>Static Page</div>"
    finally:
        os.unlink(jsx_path)


async def test_register_static_with_app_prefix(ps):
    with tempfile.NamedTemporaryFile(suffix=".jsx", mode="w", delete=False) as f:
        f.write("<div>Sage Dashboard</div>")
        jsx_path = f.name
    try:
        await ps.register_static("dashboard", jsx_path, app_name="sage")
        source = await ps.store.get_page_source("sage-dashboard")
        assert source == "<div>Sage Dashboard</div>"
    finally:
        os.unlink(jsx_path)


async def test_register_static_upserts_on_repeat(ps):
    """Calling register_static twice for the same page updates rather than errors."""
    with tempfile.NamedTemporaryFile(suffix=".jsx", mode="w", delete=False) as f:
        f.write("<div>v1</div>")
        jsx_path = f.name
    try:
        await ps.register_static("repeated", jsx_path)
        # Overwrite file and re-register
        Path(jsx_path).write_text("<div>v2</div>")
        await ps.register_static("repeated", jsx_path)
        source = await ps.store.get_page_source("repeated")
        assert source == "<div>v2</div>"
    finally:
        os.unlink(jsx_path)


# ---------------------------------------------------------------------------
# No auth required for page server GET routes
# ---------------------------------------------------------------------------

def test_page_routes_require_no_auth(client, auth_headers):
    client.post(
        "/api/tools/create_page",
        json={"name": "public-page", "jsx_code": "<p>public</p>"},
        headers=auth_headers,
    )
    # No auth header — should still succeed
    assert client.get("/api/pages").status_code == 200
    assert client.get("/api/pages/public-page/source").status_code == 200
    assert client.get("/api/pages/public-page/meta").status_code == 200
