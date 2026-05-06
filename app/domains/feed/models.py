from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class FeedSource:
    id: int
    name: str
    url: str
    enabled: bool
    created_at: str


@dataclass(frozen=True)
class ParsedFeedItem:
    title: str
    url: str
    guid: str | None
    published_at: str | None
    raw_content: str | None


@dataclass(frozen=True)
class FeedItem:
    id: int
    source_id: int
    title: str
    url: str
    guid: str | None
    published_at: str | None
    content_hash: str
    raw_content: str | None
    created_at: str


@dataclass(frozen=True)
class FetchResult:
    created: int = 0
    duplicates: int = 0
    failed: int = 0
    source_count: int = 0
    item_count: int = 0
