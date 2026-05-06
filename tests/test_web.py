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
            return type(
                "R",
                (),
                {
                    "source_count": 3,
                    "item_count": 4,
                    "created": 1,
                    "duplicates": 2,
                    "failed": 0,
                },
            )()

    class FakeDraftService:
        def __init__(self, conn, ollama):
            pass

        def generate_missing_drafts(self, limit):
            from app.domains.drafts.service import DraftGenerationSummary

            return DraftGenerationSummary(
                target=0, generated=0, failed=0, ollama_unavailable=False
            )

    monkeypatch.setattr("app.web.main.FeedService", FakeFeedService)
    monkeypatch.setattr("app.web.main.DraftService", FakeDraftService)
    client = TestClient(create_app())

    response = client.post("/internal/feed/fetch")

    assert response.status_code == 200
    body = response.json()
    assert body["created"] == 1
    assert body["source_count"] == 3
    assert body["drafts_target"] == 0
    assert body["drafts_generated"] == 0
    assert body["drafts_failed"] == 0
    assert body["ollama_unavailable"] is False


def test_feed_fetch_endpoint_returns_draft_generation_summary(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_FEED_DB_PATH", str(tmp_path / "ai-feed.db"))
    monkeypatch.setenv("AI_FEED_DRAFT_GENERATION_LIMIT", "5")

    class FakeFeedService:
        def __init__(self, conn):
            pass

        def fetch_all(self):
            return type(
                "R",
                (),
                {
                    "source_count": 3,
                    "item_count": 1807,
                    "created": 0,
                    "duplicates": 1807,
                    "failed": 0,
                },
            )()

    received_limits = []

    class FakeDraftService:
        def __init__(self, conn, ollama):
            pass

        def generate_missing_drafts(self, limit):
            from app.domains.drafts.service import DraftGenerationSummary

            received_limits.append(limit)
            return DraftGenerationSummary(
                target=5, generated=5, failed=0, ollama_unavailable=False
            )

    monkeypatch.setattr("app.web.main.FeedService", FakeFeedService)
    monkeypatch.setattr("app.web.main.DraftService", FakeDraftService)
    client = TestClient(create_app())

    response = client.post("/internal/feed/fetch")

    assert response.status_code == 200
    body = response.json()
    assert received_limits == [5]
    assert body["duplicates"] == 1807
    assert body["drafts_target"] == 5
    assert body["drafts_generated"] == 5
    assert body["ollama_unavailable"] is False


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
