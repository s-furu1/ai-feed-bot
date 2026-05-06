from __future__ import annotations

from app.main import main


def test_main_starts_with_temp_db(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AI_FEED_DB_PATH", str(tmp_path / "ai-feed.db"))
    monkeypatch.delenv("AI_FEED_ENABLE_SLACK", raising=False)
    monkeypatch.delenv("AI_FEED_ENABLE_WORKER", raising=False)
    assert main() == 0
    output = capsys.readouterr().out
    assert "ai-feed-bot started" in output
    assert "ai-feed-bot stopped" in output


def test_main_waits_when_worker_enabled(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setenv("AI_FEED_DB_PATH", str(tmp_path / "ai-feed.db"))
    monkeypatch.setenv("AI_FEED_ENABLE_WORKER", "true")
    monkeypatch.delenv("AI_FEED_ENABLE_SLACK", raising=False)
    monkeypatch.setattr("app.main.wait_forever", lambda: calls.append("wait"))

    assert main() == 0
    assert calls == ["wait"]


def test_main_calls_slack_when_enabled(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setenv("AI_FEED_DB_PATH", str(tmp_path / "ai-feed.db"))
    monkeypatch.setenv("AI_FEED_ENABLE_SLACK", "true")
    monkeypatch.delenv("AI_FEED_ENABLE_WORKER", raising=False)

    def fake_start_slack(settings):
        calls.append(settings.ai_feed_enable_slack)
        return False

    monkeypatch.setattr("app.slack.main.start_slack_if_configured", fake_start_slack)

    assert main() == 0
    assert calls == [True]
