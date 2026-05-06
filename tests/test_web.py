from __future__ import annotations

from fastapi.testclient import TestClient

from app.core.db import connect, run_migrations
from app.domains.drafts.repository import insert_draft
from app.domains.feed.models import ParsedFeedItem
from app.domains.feed.repository import insert_item, upsert_source
from app.web.main import create_app


def test_healthz_returns_200(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_FEED_DB_PATH", str(tmp_path / "ai-feed.db"))
    client = TestClient(create_app())

    response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_feed_fetch_endpoint_uses_service(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_FEED_DB_PATH", str(tmp_path / "ai-feed.db"))

    class FakeFeedService:
        def __init__(self, conn):
            pass

        def fetch_all(self):
            return type("R", (), {"created": 1, "duplicates": 2, "failed": 0})()

    monkeypatch.setattr("app.web.main.FeedService", FakeFeedService)
    client = TestClient(create_app())

    response = client.post("/internal/feed/fetch")

    assert response.status_code == 200
    assert response.json()["created"] == 1


def test_pending_drafts_endpoint_returns_drafts(monkeypatch, tmp_path):
    db_path = tmp_path / "ai-feed.db"
    monkeypatch.setenv("AI_FEED_DB_PATH", str(db_path))
    with connect(str(db_path)) as conn:
        run_migrations(conn)
        source_id = upsert_source(conn, "Test", "https://example.com/feed")
        item_id = insert_item(
            conn,
            source_id,
            ParsedFeedItem("Title", "https://example.com/a", "g", None, "raw"),
            "hash",
        )
        insert_draft(conn, item_id, "summary", "relevance", "draft", "pending")

    response = TestClient(create_app()).get("/internal/drafts/pending")

    assert response.status_code == 200
    draft = response.json()["drafts"][0]
    assert draft["title"] == "Title"
    assert draft["status"] == "pending"


def test_draft_action_endpoint_updates_status(monkeypatch, tmp_path):
    db_path = tmp_path / "ai-feed.db"
    monkeypatch.setenv("AI_FEED_DB_PATH", str(db_path))
    with connect(str(db_path)) as conn:
        run_migrations(conn)
        source_id = upsert_source(conn, "Test", "https://example.com/feed")
        item_id = insert_item(
            conn,
            source_id,
            ParsedFeedItem("Title", "https://example.com/a", "g", None, "raw"),
            "hash",
        )
        draft_id = insert_draft(conn, item_id, "summary", "relevance", "draft", "pending")

    response = TestClient(create_app()).post(f"/internal/drafts/{draft_id}/hold")

    assert response.status_code == 200
    assert response.json()["draft"]["status"] == "held"
