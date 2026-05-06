from __future__ import annotations

import sqlite3

from app.core.time import utc_now_iso
from app.domains.drafts.models import GeneratedDraft


def insert_draft(
    conn: sqlite3.Connection,
    feed_item_id: int,
    summary: str,
    relevance_comment: str | None,
    x_draft: str,
    status: str = "pending",
) -> int:
    now = utc_now_iso()
    cursor = conn.execute(
        """
        INSERT INTO generated_drafts
          (feed_item_id, summary, relevance_comment, x_draft, status, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (feed_item_id, summary, relevance_comment, x_draft, status, now, now),
    )
    conn.commit()
    return int(cursor.lastrowid)


def get_draft(conn: sqlite3.Connection, draft_id: int) -> GeneratedDraft | None:
    row = conn.execute("SELECT * FROM generated_drafts WHERE id = ?", (draft_id,)).fetchone()
    if row is None:
        return None
    return GeneratedDraft(
        id=int(row["id"]),
        feed_item_id=int(row["feed_item_id"]),
        summary=row["summary"],
        relevance_comment=row["relevance_comment"],
        x_draft=row["x_draft"],
        status=row["status"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def update_status(conn: sqlite3.Connection, draft_id: int, status: str) -> None:
    conn.execute(
        "UPDATE generated_drafts SET status = ?, updated_at = ? WHERE id = ?",
        (status, utc_now_iso(), draft_id),
    )
    conn.commit()


def count_by_status(conn: sqlite3.Connection, status: str) -> int:
    row = conn.execute(
        "SELECT COUNT(*) AS count FROM generated_drafts WHERE status = ?", (status,)
    ).fetchone()
    return int(row["count"])


def list_by_status(conn: sqlite3.Connection, status: str, limit: int = 10) -> list[GeneratedDraft]:
    rows = conn.execute(
        "SELECT * FROM generated_drafts WHERE status = ? ORDER BY id DESC LIMIT ?",
        (status, limit),
    ).fetchall()
    return [
        GeneratedDraft(
            id=int(row["id"]),
            feed_item_id=int(row["feed_item_id"]),
            summary=row["summary"],
            relevance_comment=row["relevance_comment"],
            x_draft=row["x_draft"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
        for row in rows
    ]

