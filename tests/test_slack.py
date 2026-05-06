from __future__ import annotations

from contextlib import contextmanager

from app.core.config import load_settings
from app.core.db import connect, run_migrations
from app.domains.feed.models import FetchResult
from app.slack.blocks import DRAFT_ACTION_IDS, PANEL_ACTION_IDS, ai_feed_panel_blocks
from app.slack.handlers import handle_draft_action, handle_feed_fetch_run
from app.slack.main import PANEL_SHOW_ACTION_IDS, register_action_handlers


def _action_ids(blocks):
    ids = set()
    for block in blocks:
        for element in block.get("elements", []):
            if "action_id" in element:
                ids.add(element["action_id"])
    return ids


class FakeFeedService:
    def __init__(self):
        self.called = False

    def fetch_all(self):
        self.called = True
        return FetchResult(created=1, duplicates=2, failed=0)


class FakeDraftService:
    def __init__(self):
        self.status = None

    def approve(self, draft_id):
        self.status = ("approved", draft_id)
        return self.status

    def hold(self, draft_id):
        self.status = ("held", draft_id)
        return self.status

    def reject(self, draft_id):
        self.status = ("rejected", draft_id)
        return self.status

    def regenerate(self, draft_id):
        self.status = ("regenerated", draft_id)
        return self.status


def test_ai_feed_panel_contains_expected_action_ids():
    blocks = ai_feed_panel_blocks(3, 2, 1, ["Article"])
    assert PANEL_ACTION_IDS <= _action_ids(blocks)


def test_feed_fetch_action_acks_before_fetch(tmp_path):
    order = []
    service = FakeFeedService()
    with connect(str(tmp_path / "ai-feed.db")) as conn:
        run_migrations(conn)

        def ack():
            order.append("ack")

        handle_feed_fetch_run(ack, service, conn)
        order.append("done")
        assert order[0] == "ack"
        assert service.called is True
        assert conn.execute("SELECT COUNT(*) FROM events").fetchone()[0] == 1


def test_draft_actions_update_status_after_ack():
    for action_id in DRAFT_ACTION_IDS:
        order = []
        service = FakeDraftService()

        def ack():
            order.append("ack")

        payload = {"actions": [{"value": "42"}]}
        handle_draft_action(ack, service, action_id, payload)
        assert order == ["ack"]
        assert service.status[1] == 42


class FakeApp:
    def __init__(self):
        self.registered: dict[str, object] = {}

    def action(self, action_id: str):
        def decorator(fn):
            self.registered[action_id] = fn
            return fn

        return decorator


def _wired_db_ctx(tmp_path):
    @contextmanager
    def db_ctx():
        with connect(str(tmp_path / "wired.db")) as conn:
            run_migrations(conn)
            yield conn

    return db_ctx


def test_register_action_handlers_covers_all_panel_and_draft_action_ids(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("AI_FEED_DB_PATH", str(tmp_path / "ai-feed.db"))
    settings = load_settings()
    fake_app = FakeApp()
    register_action_handlers(fake_app, settings)
    expected = PANEL_ACTION_IDS | DRAFT_ACTION_IDS
    assert expected <= set(fake_app.registered)


def test_register_action_handlers_feed_fetch_run_invokes_pure_handler(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("AI_FEED_DB_PATH", str(tmp_path / "ai-feed.db"))
    settings = load_settings()
    fake_feed = FakeFeedService()
    fake_app = FakeApp()
    register_action_handlers(
        fake_app,
        settings,
        feed_service_factory=lambda conn: fake_feed,
        db_context_factory=_wired_db_ctx(tmp_path),
    )

    order: list[str] = []

    def ack():
        order.append("ack")

    fake_app.registered["feed.fetch.run"](ack=ack, body={})
    assert order[0] == "ack"
    assert fake_feed.called is True


def test_register_action_handlers_draft_actions_invoke_pure_handler(
    monkeypatch, tmp_path
):
    monkeypatch.setenv("AI_FEED_DB_PATH", str(tmp_path / "ai-feed.db"))
    settings = load_settings()
    db_ctx = _wired_db_ctx(tmp_path)
    for action_id in DRAFT_ACTION_IDS:
        fake_draft = FakeDraftService()
        fake_app = FakeApp()
        register_action_handlers(
            fake_app,
            settings,
            draft_service_factory=lambda conn, _draft=fake_draft: _draft,
            db_context_factory=db_ctx,
        )

        order: list[str] = []

        def ack():
            order.append("ack")

        fake_app.registered[action_id](ack=ack, body={"actions": [{"value": "42"}]})
        assert order[0] == "ack"
        assert fake_draft.status is not None
        assert fake_draft.status[1] == 42


def test_register_action_handlers_panel_show_acks_only(monkeypatch, tmp_path):
    monkeypatch.setenv("AI_FEED_DB_PATH", str(tmp_path / "ai-feed.db"))
    settings = load_settings()
    fake_app = FakeApp()
    register_action_handlers(fake_app, settings)
    for action_id in PANEL_SHOW_ACTION_IDS:
        order: list[str] = []

        def ack():
            order.append("ack")

        fake_app.registered[action_id](ack=ack)
        assert order == ["ack"]

