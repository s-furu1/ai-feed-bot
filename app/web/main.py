from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from typing import Iterator

from fastapi import FastAPI, HTTPException

from app.core.config import load_settings
from app.core.db import connect, run_migrations
from app.domains.drafts.repository import list_by_status
from app.domains.drafts.service import DraftService
from app.domains.feed.service import FeedService
from app.ollama.client import OllamaClient


@contextmanager
def open_db() -> Iterator[sqlite3.Connection]:
    settings = load_settings()
    conn = connect(settings.ai_feed_db_path)
    try:
        run_migrations(conn)
        yield conn
    finally:
        conn.close()


def create_app() -> FastAPI:
    app = FastAPI(title="ai-feed-bot internal API")

    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/internal/feed/fetch")
    def fetch_feed() -> dict:
        with open_db() as conn:
            result = FeedService(conn).fetch_all()
            return {
                "ok": True,
                "created": result.created,
                "duplicates": result.duplicates,
                "failed": result.failed,
                "errors": [],
            }

    @app.get("/internal/drafts/pending")
    def pending_drafts() -> dict:
        with open_db() as conn:
            return {
                "ok": True,
                "drafts": [_draft_payload(conn, draft) for draft in list_by_status(conn, "pending")],
            }

    @app.get("/internal/drafts/held")
    def held_drafts() -> dict:
        with open_db() as conn:
            return {
                "ok": True,
                "drafts": [_draft_payload(conn, draft) for draft in list_by_status(conn, "held")],
            }

    @app.post("/internal/drafts/{draft_id}/approve")
    def approve_draft(draft_id: int) -> dict:
        return _set_draft_status(draft_id, "approve")

    @app.post("/internal/drafts/{draft_id}/hold")
    def hold_draft(draft_id: int) -> dict:
        return _set_draft_status(draft_id, "hold")

    @app.post("/internal/drafts/{draft_id}/reject")
    def reject_draft(draft_id: int) -> dict:
        return _set_draft_status(draft_id, "reject")

    @app.post("/internal/drafts/{draft_id}/regenerate")
    def regenerate_draft(draft_id: int) -> dict:
        return _set_draft_status(draft_id, "regenerate")

    return app


def _set_draft_status(draft_id: int, action: str) -> dict:
    settings = load_settings()
    with open_db() as conn:
        service = DraftService(
            conn,
            OllamaClient(settings.ollama_base_url, settings.ollama_model),
        )
        try:
            draft = getattr(service, action)(draft_id)
        except ValueError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"ok": True, "draft": _draft_payload(conn, draft)}


def _draft_payload(conn: sqlite3.Connection, draft) -> dict:
    item = conn.execute(
        "SELECT title, url FROM feed_items WHERE id = ?",
        (draft.feed_item_id,),
    ).fetchone()
    return {
        "id": draft.id,
        "title": item["title"] if item else "",
        "url": item["url"] if item else "",
        "summary": draft.summary,
        "relevance_comment": draft.relevance_comment,
        "x_draft": draft.x_draft,
        "status": draft.status,
    }


app = create_app()


def main() -> None:
    import uvicorn

    settings = load_settings()
    uvicorn.run("app.web.main:app", host=settings.ai_feed_web_host, port=settings.ai_feed_web_port)
