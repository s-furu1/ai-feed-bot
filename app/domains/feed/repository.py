from __future__ import annotations

import sqlite3

from app.core.time import utc_now_iso
from app.domains.feed.models import FeedItem, FeedSource, ParsedFeedItem


def upsert_source(conn: sqlite3.Connection, name: str, url: str, enabled: bool = True) -> int:
    conn.execute(
        """
        INSERT INTO feed_sources (name, url, enabled, created_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(url) DO UPDATE SET
          name = excluded.name,
          enabled = excluded.enabled
        """,
        (name, url, 1 if enabled else 0, utc_now_iso()),
    )
    conn.commit()
    row = conn.execute("SELECT id FROM feed_sources WHERE url = ?", (url,)).fetchone()
    return int(row["id"])


def list_enabled_sources(conn: sqlite3.Connection) -> list[FeedSource]:
    rows = conn.execute(
        "SELECT * FROM feed_sources WHERE enabled = 1 ORDER BY id"
    ).fetchall()
    return [
        FeedSource(
            id=int(row["id"]),
            name=row["name"],
            url=row["url"],
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
        )
        for row in rows
    ]


def list_sources(conn: sqlite3.Connection) -> list[FeedSource]:
    rows = conn.execute("SELECT * FROM feed_sources ORDER BY id").fetchall()
    return [
        FeedSource(
            id=int(row["id"]),
            name=row["name"],
            url=row["url"],
            enabled=bool(row["enabled"]),
            created_at=row["created_at"],
        )
        for row in rows
    ]


def insert_item(
    conn: sqlite3.Connection,
    source_id: int,
    item: ParsedFeedItem,
    content_hash: str,
) -> int | None:
    cursor = conn.execute(
        """
        INSERT OR IGNORE INTO feed_items
          (source_id, title, url, guid, published_at, content_hash, raw_content, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_id,
            item.title,
            item.url,
            item.guid,
            item.published_at,
            content_hash,
            item.raw_content,
            utc_now_iso(),
        ),
    )
    conn.commit()
    if cursor.rowcount == 0:
        return None
    return int(cursor.lastrowid)


def get_item(conn: sqlite3.Connection, feed_item_id: int) -> FeedItem | None:
    row = conn.execute("SELECT * FROM feed_items WHERE id = ?", (feed_item_id,)).fetchone()
    if row is None:
        return None
    return FeedItem(
        id=int(row["id"]),
        source_id=int(row["source_id"]),
        title=row["title"],
        url=row["url"],
        guid=row["guid"],
        published_at=row["published_at"],
        content_hash=row["content_hash"],
        raw_content=row["raw_content"],
        created_at=row["created_at"],
    )


def list_undrafted_items(conn: sqlite3.Connection, limit: int) -> list[FeedItem]:
    rows = conn.execute(
        """
        SELECT feed_items.*
        FROM feed_items
        LEFT JOIN generated_drafts
          ON generated_drafts.feed_item_id = feed_items.id
        WHERE generated_drafts.id IS NULL
        ORDER BY feed_items.id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    return [
        FeedItem(
            id=int(row["id"]),
            source_id=int(row["source_id"]),
            title=row["title"],
            url=row["url"],
            guid=row["guid"],
            published_at=row["published_at"],
            content_hash=row["content_hash"],
            raw_content=row["raw_content"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


def count_undrafted_items(conn: sqlite3.Connection) -> int:
    row = conn.execute(
        """
        SELECT COUNT(*) AS count
        FROM feed_items
        LEFT JOIN generated_drafts
          ON generated_drafts.feed_item_id = feed_items.id
        WHERE generated_drafts.id IS NULL
        """
    ).fetchone()
    return int(row["count"])


def list_recent_items(conn: sqlite3.Connection, limit: int = 5) -> list[FeedItem]:
    rows = conn.execute(
        "SELECT * FROM feed_items ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    return [
        FeedItem(
            id=int(row["id"]),
            source_id=int(row["source_id"]),
            title=row["title"],
            url=row["url"],
            guid=row["guid"],
            published_at=row["published_at"],
            content_hash=row["content_hash"],
            raw_content=row["raw_content"],
            created_at=row["created_at"],
        )
        for row in rows
    ]

