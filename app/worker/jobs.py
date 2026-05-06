from __future__ import annotations

import sqlite3
from typing import Callable

from app.domains.events.service import record_event


def run_fetch_job(feed_service):
    return feed_service.fetch_all()


def run_draft_generation_job(draft_service, feed_item_ids: list[int]) -> list[int]:
    return [draft_service.generate_for_item(feed_item_id) for feed_item_id in feed_item_ids]


def run_notification_job(
    conn: sqlite3.Connection,
    notify: Callable[[], None],
) -> bool:
    try:
        notify()
    except Exception as exc:
        record_event(
            conn,
            "notification.failed",
            "worker",
            {"error": str(exc)},
        )
        return False
    record_event(conn, "notification.sent", "worker", {})
    return True

