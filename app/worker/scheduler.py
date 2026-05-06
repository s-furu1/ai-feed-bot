from __future__ import annotations

from dataclasses import dataclass

from app.core.config import Settings


@dataclass(frozen=True)
class WorkerSchedule:
    fetch_interval_minutes: int


def build_schedule(settings: Settings) -> WorkerSchedule:
    return WorkerSchedule(
        fetch_interval_minutes=settings.ai_feed_fetch_interval_minutes,
    )

