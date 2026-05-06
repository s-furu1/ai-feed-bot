from __future__ import annotations

from pathlib import Path

import pytest

from app.core.db import connect, run_migrations
from app.domains.drafts.repository import get_draft
from app.domains.drafts.service import DraftService
from app.domains.feed.models import ParsedFeedItem
from app.domains.feed.repository import list_sources
from app.domains.feed.service import FeedService


class FakeOllama:
    def generate(self, prompt: str) -> str:
        return "\n".join(
            [
                "1. AIニュースの要点",
                "2. 開発者への影響",
                "3. 今後の注目点",
                "発信テーマと関連します。",
                "AIニュースの要点を共有します。",
            ]
        )


class FailingOllama:
    def generate(self, prompt: str) -> str:
        raise RuntimeError("ollama down")


def _prepared_conn(tmp_path):
    conn = connect(str(tmp_path / "ai-feed.db"))
    run_migrations(conn)
    feed_service = FeedService(conn)
    feed_service.seed_initial_sources()
    source_id = list_sources(conn)[0].id
    item_id = feed_service.save_item(
        source_id,
        ParsedFeedItem("AI Article", "https://example.com/ai", "ai-1", None, "raw"),
    )
    return conn, item_id


def test_generate_draft_and_status_changes(tmp_path):
    conn, item_id = _prepared_conn(tmp_path)
    try:
        service = DraftService(conn, FakeOllama())
        draft_id = service.generate_for_item(item_id)
        draft = get_draft(conn, draft_id)
        assert draft is not None
        assert draft.status == "pending"
        assert "AIニュース" in draft.summary
        assert service.approve(draft_id).status == "approved"
        assert service.hold(draft_id).status == "held"
        assert service.reject(draft_id).status == "rejected"
        assert service.regenerate(draft_id).status == "regenerated"
    finally:
        conn.close()


def test_draft_generate_failure_records_event(tmp_path):
    conn, item_id = _prepared_conn(tmp_path)
    try:
        service = DraftService(conn, FailingOllama())
        with pytest.raises(RuntimeError):
            service.generate_for_item(item_id)
        event_types = [
            row["event_type"] for row in conn.execute("SELECT event_type FROM events")
        ]
        assert "draft.generate_failed" in event_types
    finally:
        conn.close()


def test_x_auto_posting_is_not_implemented():
    root = Path(__file__).resolve().parents[1] / "app"
    forbidden = ("X_API_TOKEN", "post_tweet", "create_tweet", "statuses/update")
    for path in root.rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden)


def test_generate_missing_drafts_targets_only_undrafted_items(tmp_path):
    conn, item_id = _prepared_conn(tmp_path)
    try:
        feed_service = FeedService(conn)
        source_id = list_sources(conn)[0].id
        for index in range(4):
            feed_service.save_item(
                source_id,
                ParsedFeedItem(
                    f"Article {index}",
                    f"https://example.com/a/{index}",
                    f"a-{index}",
                    None,
                    "raw",
                ),
            )
        service = DraftService(conn, FakeOllama())

        first = service.generate_missing_drafts(limit=2)
        second = service.generate_missing_drafts(limit=2)
        third = service.generate_missing_drafts(limit=2)

        assert first.target == 2
        assert first.generated == 2
        assert second.target == 2
        assert second.generated == 2
        assert third.target == 1
        assert third.generated == 1
        total = conn.execute(
            "SELECT COUNT(*) AS count FROM generated_drafts"
        ).fetchone()["count"]
        assert total == 5
    finally:
        conn.close()


def test_generate_missing_drafts_respects_limit(tmp_path):
    conn, item_id = _prepared_conn(tmp_path)
    try:
        feed_service = FeedService(conn)
        source_id = list_sources(conn)[0].id
        for index in range(10):
            feed_service.save_item(
                source_id,
                ParsedFeedItem(
                    f"Article {index}",
                    f"https://example.com/b/{index}",
                    f"b-{index}",
                    None,
                    "raw",
                ),
            )
        service = DraftService(conn, FakeOllama())

        summary = service.generate_missing_drafts(limit=5)

        assert summary.target == 5
        assert summary.generated == 5
        assert summary.failed == 0
        assert summary.ollama_unavailable is False
    finally:
        conn.close()


def test_generate_missing_drafts_records_failure_when_ollama_down(tmp_path):
    conn, item_id = _prepared_conn(tmp_path)
    try:
        service = DraftService(conn, FailingOllama())

        summary = service.generate_missing_drafts(limit=3)

        assert summary.target == 1
        assert summary.generated == 0
        assert summary.failed == 1
        assert summary.ollama_unavailable is True
        event_types = [
            row["event_type"] for row in conn.execute("SELECT event_type FROM events")
        ]
        assert "draft.generate_failed" in event_types
    finally:
        conn.close()


def test_generate_missing_drafts_with_zero_limit_is_noop(tmp_path):
    conn, item_id = _prepared_conn(tmp_path)
    try:
        service = DraftService(conn, FakeOllama())

        summary = service.generate_missing_drafts(limit=0)

        assert summary.target == 0
        assert summary.generated == 0
    finally:
        conn.close()
