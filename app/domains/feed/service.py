from __future__ import annotations

import hashlib
import sqlite3
import urllib.request
import xml.etree.ElementTree as ET

from app.domains.events.service import record_event
from app.domains.feed import repository
from app.domains.feed.models import FetchResult, ParsedFeedItem


INITIAL_SOURCES = (
    ("Hugging Face Blog", "https://huggingface.co/blog/feed.xml"),
    ("OpenAI News", "https://openai.com/news/rss.xml"),
    ("Google DeepMind", "https://deepmind.google/blog/rss.xml"),
)


def seed_default_sources(conn: sqlite3.Connection) -> int:
    before = {source.url for source in repository.list_sources(conn)}
    for name, url in INITIAL_SOURCES:
        repository.upsert_source(conn, name, url, enabled=True)
    after = {source.url for source in repository.list_sources(conn)}
    added = len(after - before)
    record_event(
        conn,
        "feed.sources.seeded",
        "feed",
        {"source_count": len(after), "added": added},
    )
    return added


def seed_initial_sources(conn: sqlite3.Connection) -> None:
    seed_default_sources(conn)


def content_hash_for(item: ParsedFeedItem) -> str:
    base = "|".join([item.title.strip(), item.url.strip(), item.guid or ""])
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


def parse_rss(xml_text: str) -> list[ParsedFeedItem]:
    root = ET.fromstring(xml_text)
    items: list[ParsedFeedItem] = []
    for node in root.findall(".//item"):
        title = _node_text(node, "title")
        url = _node_text(node, "link")
        guid = _node_text(node, "guid") or url
        published_at = _node_text(node, "pubDate")
        raw_content = _node_text(node, "description")
        if title and url:
            items.append(ParsedFeedItem(title, url, guid, published_at, raw_content))
    for node in root.findall(".//{http://www.w3.org/2005/Atom}entry"):
        title = _node_text(node, "{http://www.w3.org/2005/Atom}title")
        link_node = node.find("{http://www.w3.org/2005/Atom}link")
        url = ""
        if link_node is not None:
            url = link_node.attrib.get("href", "")
        guid = _node_text(node, "{http://www.w3.org/2005/Atom}id") or url
        published_at = _node_text(node, "{http://www.w3.org/2005/Atom}updated")
        raw_content = _node_text(node, "{http://www.w3.org/2005/Atom}summary")
        if title and url:
            items.append(ParsedFeedItem(title, url, guid, published_at, raw_content))
    return items


def _node_text(node: ET.Element, tag: str) -> str:
    child = node.find(tag)
    if child is None or child.text is None:
        return ""
    return child.text.strip()


class FeedService:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def seed_initial_sources(self) -> None:
        seed_default_sources(self.conn)

    def save_item(self, source_id: int, item: ParsedFeedItem) -> int | None:
        content_hash = content_hash_for(item)
        item_id = repository.insert_item(self.conn, source_id, item, content_hash)
        if item_id is None:
            record_event(
                self.conn,
                "feed.item.duplicate",
                "feed",
                {"source_id": source_id, "content_hash": content_hash},
            )
            return None
        record_event(
            self.conn,
            "feed.item.created",
            "feed",
            {"source_id": source_id, "feed_item_id": item_id},
        )
        return item_id

    def fetch_all(self) -> FetchResult:
        seed_default_sources(self.conn)
        record_event(self.conn, "feed.fetch.started", "feed", {})
        sources = repository.list_enabled_sources(self.conn)
        source_count = len(sources)
        item_count = 0
        created = 0
        duplicates = 0
        failed = 0
        for source in sources:
            try:
                xml_text = fetch_text(source.url)
                items = parse_rss(xml_text)
                item_count += len(items)
                for item in items:
                    if self.save_item(source.id, item) is None:
                        duplicates += 1
                    else:
                        created += 1
            except Exception as exc:
                failed += 1
                record_event(
                    self.conn,
                    "feed.fetch.failed",
                    "feed",
                    {"source_id": source.id, "error": str(exc)},
                )
        record_event(
            self.conn,
            "feed.fetch.completed",
            "feed",
            {
                "source_count": source_count,
                "item_count": item_count,
                "created": created,
                "duplicates": duplicates,
                "failed": failed,
            },
        )
        return FetchResult(
            source_count=source_count,
            item_count=item_count,
            created=created,
            duplicates=duplicates,
            failed=failed,
        )

    def recent_items(self, limit: int = 5):
        return repository.list_recent_items(self.conn, limit)


def fetch_text(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": "ai-feed-bot/0.1"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8")
