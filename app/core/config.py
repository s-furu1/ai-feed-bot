from __future__ import annotations

import os
from dataclasses import dataclass


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return int(value)


def _env_positive_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        parsed = int(value)
    except ValueError:
        return default
    if parsed <= 0:
        return default
    return parsed


@dataclass(frozen=True)
class Settings:
    app_env: str
    log_level: str
    ai_feed_db_path: str
    ai_feed_enable_slack: bool
    ai_feed_enable_worker: bool
    ai_feed_enable_web: bool
    ai_feed_web_host: str
    ai_feed_web_port: int
    slack_bot_token: str | None
    slack_app_token: str | None
    slack_signing_secret: str | None
    slack_channel_ai_feed: str | None
    ollama_base_url: str
    ollama_model: str
    ollama_timeout_seconds: int
    ollama_keep_alive: str
    ai_feed_fetch_interval_minutes: int
    ai_feed_draft_generation_limit: int


def load_settings() -> Settings:
    return Settings(
        app_env=os.getenv("APP_ENV", "local"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        ai_feed_db_path=os.getenv("AI_FEED_DB_PATH", "/data/ai-feed.db"),
        ai_feed_enable_slack=_env_bool("AI_FEED_ENABLE_SLACK", False),
        ai_feed_enable_worker=_env_bool("AI_FEED_ENABLE_WORKER", False),
        ai_feed_enable_web=_env_bool("AI_FEED_ENABLE_WEB", False),
        ai_feed_web_host=os.getenv("AI_FEED_WEB_HOST", "0.0.0.0"),
        ai_feed_web_port=_env_int("AI_FEED_WEB_PORT", 8000),
        slack_bot_token=os.getenv("SLACK_BOT_TOKEN") or None,
        slack_app_token=os.getenv("SLACK_APP_TOKEN") or None,
        slack_signing_secret=os.getenv("SLACK_SIGNING_SECRET") or None,
        slack_channel_ai_feed=os.getenv("SLACK_CHANNEL_AI_FEED") or None,
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen3.5:9b"),
        ollama_timeout_seconds=_env_positive_int("OLLAMA_TIMEOUT_SECONDS", 300),
        ollama_keep_alive=os.getenv("OLLAMA_KEEP_ALIVE", "10m") or "10m",
        ai_feed_fetch_interval_minutes=_env_int("AI_FEED_FETCH_INTERVAL_MINUTES", 60),
        ai_feed_draft_generation_limit=_env_int("AI_FEED_DRAFT_GENERATION_LIMIT", 5),
    )
