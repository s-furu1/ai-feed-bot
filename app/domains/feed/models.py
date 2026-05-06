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
    created: int
    duplicates: int
    failed: int

