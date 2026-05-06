from __future__ import annotations

from app.domains.drafts.models import GeneratedDraft
from app.domains.feed.models import FeedItem


PANEL_ACTION_IDS = {
    "feed.fetch.run",
    "feed.pending.show",
    "feed.held.show",
    "feed.settings.show",
}

DRAFT_ACTION_IDS = {
    "draft.approve",
    "draft.hold",
    "draft.reject",
    "draft.regenerate",
}


def ai_feed_panel_blocks(
    unchecked_count: int,
    pending_count: int,
    held_count: int,
    recent_titles: list[str],
) -> list[dict]:
    recent = "\n".join(f"- {title}" for title in recent_titles) or "直近記事はありません"
    return [
        {"type": "header", "text": {"type": "plain_text", "text": "AI Feed"}},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"未確認記事: {unchecked_count}件\n"
                    f"pending draft: {pending_count}件\n"
                    f"held draft: {held_count}件\n\n"
                    f"直近記事:\n{recent}"
                ),
            },
        },
        {
            "type": "actions",
            "elements": [
                _button("新着取得", "feed.fetch.run"),
                _button("未確認を見る", "feed.pending.show"),
                _button("保留を見る", "feed.held.show"),
                _button("設定", "feed.settings.show"),
            ],
        },
    ]


def draft_message_blocks(draft: GeneratedDraft, item: FeedItem) -> list[dict]:
    return [
        {"type": "header", "text": {"type": "plain_text", "text": "AI Feed"}},
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*タイトル:*\n{item.title}\n\n"
                    f"*3行要約:*\n{draft.summary}\n\n"
                    f"*発信テーマとの関連:*\n{draft.relevance_comment or ''}\n\n"
                    f"*X下書き:*\n{draft.x_draft}"
                ),
            },
        },
        {
            "type": "actions",
            "elements": [
                _button("採用", "draft.approve", str(draft.id)),
                _button("保留", "draft.hold", str(draft.id)),
                _button("破棄", "draft.reject", str(draft.id)),
                _button("再生成", "draft.regenerate", str(draft.id)),
            ],
        },
    ]


def _button(text: str, action_id: str, value: str | None = None) -> dict:
    block = {
        "type": "button",
        "text": {"type": "plain_text", "text": text},
        "action_id": action_id,
    }
    if value is not None:
        block["value"] = value
    return block

