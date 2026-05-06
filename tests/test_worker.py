from __future__ import annotations

from app.core.config import load_settings
from app.core.db import connect, run_migrations
from app.worker.jobs import run_notification_job
from app.worker.main import start_worker_if_enabled
from app.worker.scheduler import build_schedule


def test_worker_disabled_by_default(monkeypatch):
    monkeypatch.delenv("AI_FEED_ENABLE_WORKER", raising=False)
    settings = load_settings()
    assert start_worker_if_enabled(settings) is False


def test_worker_enabled_builds_schedule(monkeypatch):
    monkeypatch.setenv("AI_FEED_ENABLE_WORKER", "true")
    monkeypatch.setenv("AI_FEED_FETCH_INTERVAL_MINUTES", "15")
    settings = load_settings()
    schedule = build_schedule(settings)
    assert schedule.fetch_interval_minutes == 15
    assert start_worker_if_enabled(settings) is True


def test_notification_job_failure_does_not_raise(tmp_path):
    with connect(str(tmp_path / "ai-feed.db")) as conn:
        run_migrations(conn)

        def failing():
            raise RuntimeError("slack down")

        assert run_notification_job(conn, failing) is False
        event_types = [
            row["event_type"] for row in conn.execute("SELECT event_type FROM events")
        ]
        assert "notification.failed" in event_types


def test_notification_job_success_records_event(tmp_path):
    with connect(str(tmp_path / "ai-feed.db")) as conn:
        run_migrations(conn)
        assert run_notification_job(conn, lambda: None) is True
        event_types = [
            row["event_type"] for row in conn.execute("SELECT event_type FROM events")
        ]
        assert "notification.sent" in event_types

