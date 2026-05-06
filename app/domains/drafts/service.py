from __future__ import annotations

import sqlite3

from app.domains.drafts import repository
from app.domains.drafts.models import DRAFT_STATUSES, GeneratedDraft
from app.domains.events.service import record_event
from app.domains.feed.repository import get_item


class DraftService:
    def __init__(self, conn: sqlite3.Connection, ollama_client):
        self.conn = conn
        self.ollama_client = ollama_client

    def generate_for_item(self, feed_item_id: int) -> int:
        item = get_item(self.conn, feed_item_id)
        if item is None:
            raise ValueError(f"feed item not found: {feed_item_id}")
        prompt = build_prompt(item.title, item.url, item.raw_content or "")
        try:
            response_text = self.ollama_client.generate(prompt)
        except Exception as exc:
            record_event(
                self.conn,
                "draft.generate_failed",
                "draft",
                {"feed_item_id": feed_item_id, "error": str(exc)},
            )
            raise
        summary, relevance_comment, x_draft = parse_generation(response_text)
        draft_id = repository.insert_draft(
            self.conn, feed_item_id, summary, relevance_comment, x_draft, "pending"
        )
        record_event(
            self.conn,
            "draft.generated",
            "draft",
            {"feed_item_id": feed_item_id, "draft_id": draft_id},
        )
        return draft_id

    def set_status(self, draft_id: int, status: str) -> GeneratedDraft:
        if status not in DRAFT_STATUSES:
            raise ValueError(f"invalid draft status: {status}")
        repository.update_status(self.conn, draft_id, status)
        draft = repository.get_draft(self.conn, draft_id)
        if draft is None:
            raise ValueError(f"draft not found: {draft_id}")
        record_event(
            self.conn,
            f"draft.{status}",
            "draft",
            {"draft_id": draft_id, "status": status},
        )
        return draft

    def approve(self, draft_id: int) -> GeneratedDraft:
        return self.set_status(draft_id, "approved")

    def hold(self, draft_id: int) -> GeneratedDraft:
        return self.set_status(draft_id, "held")

    def reject(self, draft_id: int) -> GeneratedDraft:
        return self.set_status(draft_id, "rejected")

    def regenerate(self, draft_id: int) -> GeneratedDraft:
        return self.set_status(draft_id, "regenerated")


def build_prompt(title: str, url: str, raw_content: str) -> str:
    return (
        "以下のAI関連RSS記事について、3行要約、発信テーマとの関連、"
        "人間が手動投稿するためのX投稿下書きを日本語で作成してください。\n\n"
        f"タイトル: {title}\nURL: {url}\n本文: {raw_content}"
    )


def parse_generation(text: str) -> tuple[str, str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    if not lines:
        return ("要約を生成できませんでした。", "関連コメントを確認してください。", "")
    summary_lines = lines[:3]
    summary = "\n".join(summary_lines)
    relevance_comment = lines[3] if len(lines) > 3 else "発信テーマとの関連を確認してください。"
    x_draft = "\n".join(lines[4:]) if len(lines) > 4 else lines[-1]
    return summary, relevance_comment, x_draft[:280]

