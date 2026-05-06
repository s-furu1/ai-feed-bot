from __future__ import annotations

import sqlite3

from app.domains.drafts.repository import count_by_status
from app.domains.feed.repository import list_recent_items
from app.slack.blocks import ai_feed_panel_blocks


def build_panel_from_db(conn: sqlite3.Connection) -> list[dict]:
    recent_items = list_recent_items(conn, limit=5)
    pending_count = count_by_status(conn, "pending")
    held_count = count_by_status(conn, "held")
    return ai_feed_panel_blocks(
        unchecked_count=pending_count,
        pending_count=pending_count,
        held_count=held_count,
        recent_titles=[item.title for item in recent_items],
    )

