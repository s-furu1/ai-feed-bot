from __future__ import annotations

from app.main import main


def test_main_starts_with_temp_db(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("AI_FEED_DB_PATH", str(tmp_path / "ai-feed.db"))
    monkeypatch.delenv("AI_FEED_ENABLE_SLACK", raising=False)
    monkeypatch.delenv("AI_FEED_ENABLE_WORKER", raising=False)
    assert main() == 0
    assert "ai-feed-bot started" in capsys.readouterr().out

