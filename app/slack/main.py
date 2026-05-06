from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Callable, ContextManager, Iterator

from app.core.config import Settings
from app.core.db import connect, run_migrations
from app.domains.drafts.service import DraftService
from app.domains.feed.service import FeedService
from app.ollama.client import OllamaClient
from app.slack.blocks import DRAFT_ACTION_IDS, PANEL_ACTION_IDS
from app.slack.handlers import handle_draft_action, handle_feed_fetch_run


PANEL_SHOW_ACTION_IDS = PANEL_ACTION_IDS - {"feed.fetch.run"}


@contextmanager
def _open_db(db_path: str) -> Iterator[sqlite3.Connection]:
    conn = connect(db_path)
    try:
        run_migrations(conn)
        yield conn
    finally:
        conn.close()


def register_action_handlers(
    app,
    settings: Settings,
    *,
    feed_service_factory: Callable[[sqlite3.Connection], FeedService] | None = None,
    draft_service_factory: Callable[[sqlite3.Connection], DraftService] | None = None,
    db_context_factory: Callable[[], ContextManager[sqlite3.Connection]] | None = None,
) -> None:
    feed_factory = feed_service_factory or (lambda conn: FeedService(conn))
    draft_factory = draft_service_factory or (
        lambda conn: DraftService(
            conn,
            OllamaClient(settings.ollama_base_url, settings.ollama_model),
        )
    )
    db_ctx = db_context_factory or (lambda: _open_db(settings.ai_feed_db_path))

    def _on_feed_fetch_run(ack, body=None):
        with db_ctx() as conn:
            handle_feed_fetch_run(ack, feed_factory(conn), conn)

    app.action("feed.fetch.run")(_on_feed_fetch_run)

    def _on_panel_show(ack, body=None):
        ack()

    for action_id in PANEL_SHOW_ACTION_IDS:
        app.action(action_id)(_on_panel_show)

    def _make_draft_action(bound_action_id: str):
        def _on_draft_action(ack, body=None):
            with db_ctx() as conn:
                handle_draft_action(
                    ack, draft_factory(conn), bound_action_id, body or {}
                )
        return _on_draft_action

    for action_id in DRAFT_ACTION_IDS:
        app.action(action_id)(_make_draft_action(action_id))


def start_slack_if_configured(settings: Settings) -> bool:
    missing = [
        name
        for name, value in {
            "SLACK_BOT_TOKEN": settings.slack_bot_token,
            "SLACK_APP_TOKEN": settings.slack_app_token,
            "SLACK_SIGNING_SECRET": settings.slack_signing_secret,
            "SLACK_CHANNEL_AI_FEED": settings.slack_channel_ai_feed,
        }.items()
        if not value
    ]
    if missing:
        print(f"Slack disabled: missing {', '.join(missing)}")
        return False
    try:
        from slack_bolt import App
        from slack_bolt.adapter.socket_mode import SocketModeHandler
    except ImportError:
        print("Slack disabled: slack-bolt is not installed")
        return False

    app = App(token=settings.slack_bot_token, signing_secret=settings.slack_signing_secret)

    @app.command("/feed")
    def feed_command(ack, respond, command):
        ack()
        if command.get("text", "").strip() == "ping":
            respond("pong")
        else:
            respond("/feed ping のみ利用できます")

    register_action_handlers(app, settings)

    SocketModeHandler(app, settings.slack_app_token).start()
    return True


if __name__ == "__main__":
    from app.core.config import load_settings

    start_slack_if_configured(load_settings())
