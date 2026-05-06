from __future__ import annotations

import json

from app.core.db import connect, run_migrations
from app.domains.feed.models import ParsedFeedItem
from app.domains.feed.repository import list_sources
from app.domains.feed.service import FeedService, parse_rss, seed_default_sources


SAMPLE_RSS = """<?xml version="1.0"?>
<rss><channel>
  <item>
    <title>New AI Model</title>
    <link>https://example.com/model</link>
    <guid>model-1</guid>
    <pubDate>Tue, 05 May 2026 00:00:00 GMT</pubDate>
    <description>Details about the model.</description>
  </item>
</channel></rss>
"""


def _conn(tmp_path):
    conn = connect(str(tmp_path / "ai-feed.db"))
    run_migrations(conn)
    return conn


def test_seed_initial_sources_is_idempotent(tmp_path):
    with _conn(tmp_path) as conn:
        service = FeedService(conn)
        service.seed_initial_sources()
        service.seed_initial_sources()
        sources = list_sources(conn)
        assert [source.name for source in sources] == [
            "Hugging Face Blog",
            "OpenAI News",
            "Google DeepMind",
        ]


def test_seed_default_sources_adds_missing_sources(tmp_path):
    with _conn(tmp_path) as conn:
        seed_default_sources(conn)
        seed_default_sources(conn)
        assert len(list_sources(conn)) == 3


def test_parse_and_save_rss_item_with_duplicate_detection(tmp_path):
    with _conn(tmp_path) as conn:
        service = FeedService(conn)
        service.seed_initial_sources()
        source_id = list_sources(conn)[0].id
        item = parse_rss(SAMPLE_RSS)[0]
        first_id = service.save_item(source_id, item)
        duplicate_id = service.save_item(source_id, item)
        assert first_id is not None
        assert duplicate_id is None
        row = conn.execute("SELECT COUNT(*) AS count FROM feed_items").fetchone()
        assert row["count"] == 1
        event_types = [
            row["event_type"] for row in conn.execute("SELECT event_type FROM events")
        ]
        assert "feed.item.created" in event_types
        assert "feed.item.duplicate" in event_types


def test_fetch_all_returns_summary(monkeypatch, tmp_path):
    with _conn(tmp_path) as conn:
        service = FeedService(conn)
        monkeypatch.setattr("app.domains.feed.service.fetch_text", lambda url: SAMPLE_RSS)

        result = service.fetch_all()
        duplicate = service.fetch_all()

        assert result.source_count == 3
        assert result.item_count == 3
        assert result.created == 1
        assert result.duplicates == 2
        assert duplicate.duplicates == 3


def test_events_payload_is_valid_json(tmp_path):
    with _conn(tmp_path) as conn:
        service = FeedService(conn)
        service.seed_initial_sources()
        source_id = list_sources(conn)[0].id
        service.save_item(
            source_id,
            ParsedFeedItem("title", "https://example.com", "guid", None, "raw"),
        )
        for row in conn.execute("SELECT payload_json FROM events").fetchall():
            assert isinstance(json.loads(row["payload_json"]), dict)
