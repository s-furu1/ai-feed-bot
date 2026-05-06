from __future__ import annotations

from typing import Any, Callable

from app.domains.events.service import record_event


Ack = Callable[[], None]


def handle_feed_fetch_run(ack: Ack, feed_service, conn) -> None:
    ack()
    result = feed_service.fetch_all()
    record_event(
        conn,
        "slack.feed.fetch_run",
        "slack",
        {
            "created": result.created,
            "duplicates": result.duplicates,
            "failed": result.failed,
        },
    )


def handle_draft_action(ack: Ack, draft_service, action_id: str, payload: dict[str, Any]):
    ack()
    draft_id = int(payload["actions"][0]["value"])
    if action_id == "draft.approve":
        return draft_service.approve(draft_id)
    if action_id == "draft.hold":
        return draft_service.hold(draft_id)
    if action_id == "draft.reject":
        return draft_service.reject(draft_id)
    if action_id == "draft.regenerate":
        return draft_service.regenerate(draft_id)
    raise ValueError(f"unsupported draft action: {action_id}")

