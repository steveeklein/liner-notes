"""
Helpers for linking artist names in card content.
Prefer source links (Discogs, MusicBrainz) when available; use Wikipedia only for unlinked names.
All URLs are validated to be http/https only to prevent XSS.
"""
from urllib.parse import quote


def is_safe_url(url: str) -> bool:
    """Return True only for http or https URLs. Rejects javascript:, data:, etc. Use when building links from external data."""
    if not url or not isinstance(url, str):
        return False
    u = url.strip().lower()
    return u.startswith("https://") or u.startswith("http://")


def wikipedia_article_url(name: str) -> str:
    """Return Wikipedia article URL for an artist/page name (spaces → underscores, encoded)."""
    if not name or not name.strip():
        return "https://en.wikipedia.org/wiki/Main_Page"
    title = name.strip().replace(" ", "_")
    return f"https://en.wikipedia.org/wiki/{quote(title, safe='')}"


def artist_link_markdown(name: str, prefer_url: str | None = None) -> str:
    """Return markdown link for an artist. Use prefer_url when provided and safe (http/https); else Wikipedia."""
    if not name or not name.strip():
        return ""
    if prefer_url and prefer_url.strip() and is_safe_url(prefer_url):
        return f"[{name}]({prefer_url.strip()})"
    url = wikipedia_article_url(name)
    return f"[{name}]({url})"
