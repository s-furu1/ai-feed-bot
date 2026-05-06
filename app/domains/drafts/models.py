from __future__ import annotations

from dataclasses import dataclass


DRAFT_STATUSES = {"pending", "approved", "held", "rejected", "regenerated"}


@dataclass(frozen=True)
class GeneratedDraft:
    id: int
    feed_item_id: int
    summary: str
    relevance_comment: str | None
    x_draft: str
    status: str
    created_at: str
    updated_at: str

