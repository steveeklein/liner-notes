"""Helpers for linking artist names. Prefer source links when available; use Wikipedia only for unlinked names."""
from urllib.parse import quote


def wikipedia_article_url(name: str) -> str:
    """Return Wikipedia article URL for an artist/page name (spaces → underscores, encoded)."""
    if not name or not name.strip():
        return "https://en.wikipedia.org/wiki/Main_Page"
    title = name.strip().replace(" ", "_")
    return f"https://en.wikipedia.org/wiki/{quote(title, safe='')}"


def artist_link_markdown(name: str, prefer_url: str | None = None) -> str:
    """Return markdown link for an artist. Use prefer_url when provided (e.g. Discogs/MusicBrainz); else Wikipedia."""
    if not name or not name.strip():
        return ""
    if prefer_url and prefer_url.strip():
        return f"[{name}]({prefer_url.strip()})"
    url = wikipedia_article_url(name)
    return f"[{name}]({url})"
