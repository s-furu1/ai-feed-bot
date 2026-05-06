from __future__ import annotations

from app.core.config import Settings
from app.worker.scheduler import build_schedule


def start_worker_if_enabled(settings: Settings) -> bool:
    if not settings.ai_feed_enable_worker:
        return False
    schedule = build_schedule(settings)
    print(
        "ai-feed worker enabled: "
        f"fetch interval {schedule.fetch_interval_minutes} minutes"
    )
    return True

