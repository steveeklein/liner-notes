"""
Fetches discussions from multiple social and forum sources via web search:
Quora, Music Stack Exchange, Last.fm, and other discussion boards.
Uses DuckDuckGo HTML search (no API key). Reddit is handled by RedditSource.
"""
from typing import List
import uuid
import httpx
from urllib.parse import urlparse

from app.models import InfoCard, CardSource
from .base import DataSource


# Map known discussion/social domains to display names (for card title attribution).
# Subdomains are matched by suffix (e.g. music.stackexchange.com -> Music Stack Exchange).
DOMAIN_LABELS: dict[str, str] = {
    "quora.com": "Quora",
    "www.quora.com": "Quora",
    "music.stackexchange.com": "Music Stack Exchange",
    "stackexchange.com": "Stack Exchange",
    "stackoverflow.com": "Stack Overflow",
    "last.fm": "Last.fm",
    "www.last.fm": "Last.fm",
    "twitter.com": "X",
    "x.com": "X",
    "tumblr.com": "Tumblr",
    "genius.com": "Genius",
    "songfacts.com": "Songfacts",
    "songmeanings.com": "SongMeanings",
    "stevehoffman.tv": "Steve Hoffman Forums",
    "forums.stevehoffman.tv": "Steve Hoffman Forums",
    "ultimate-guitar.com": "Ultimate Guitar",
    "reddit.com": "Reddit",  # we have RedditSource; include here only if we want more coverage
    "old.reddit.com": "Reddit",
    "rateyourmusic.com": "Rate Your Music",
    "sonemic.com": "Sonemic",
    "discogs.com": "Discogs",
    "allmusic.com": "AllMusic",
    "pitchfork.com": "Pitchfork",
    "albumoftheyear.org": "Album of the Year",
    "sputnikmusic.com": "Sputnikmusic",
    "metacritic.com": "Metacritic",
    "avclub.com": "The A.V. Club",
    "nme.com": "NME",
    "rollingstone.com": "Rolling Stone",
    "billboard.com": "Billboard",
    "bluesky.app": "Bluesky",
    "bsky.app": "Bluesky",
}


def _domain_label(url: str) -> str:
    """Return a friendly label for the result's domain, or 'Discussion'."""
    if not url:
        return "Discussion"
    try:
        parsed = urlparse(url)
        host = (parsed.netloc or "").strip().lower()
        if not host:
            return "Discussion"
        # Strip leading www.
        if host.startswith("www."):
            host = host[4:]
        # Direct match
        if host in DOMAIN_LABELS:
            return DOMAIN_LABELS[host]
        # Suffix match for subdomains (e.g. music.stackexchange.com)
        for domain, label in DOMAIN_LABELS.items():
            if host == domain or host.endswith("." + domain):
                return label
        # Generic forum/board patterns
        if "forum" in host or "board" in host or "community" in host:
            return "Forum"
        return "Discussion"
    except Exception:
        return "Discussion"


class DiscussionSearchSource(DataSource):
    """Fetches discussion-style results from Quora, Stack Exchange, forums, and similar sites."""

    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) LinerNotes/1.0"
        }

    def _extract_href(self, href: str) -> str:
        """Extract real URL from DDG redirect link if needed."""
        if not href or not href.strip():
            return href
        if "uddg=" in href:
            from urllib.parse import urlparse, parse_qs
            try:
                parsed = urlparse(href)
                q = parse_qs(parsed.query)
                uddg = q.get("uddg", [])
                if uddg:
                    return uddg[0]
            except Exception:
                pass
        return href

    async def _search_ddg_html(self, query: str, max_results: int = 6) -> List[dict]:
        """Run DuckDuckGo HTML search and return list of {title, snippet, url}."""
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                    headers=self.headers,
                    timeout=12.0,
                )
                if response.status_code != 200:
                    return []
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(response.text, "html.parser")
                results = []
                # Primary selectors (current DDG structure)
                for result in soup.select(".result")[:max_results]:
                    title_elem = result.select_one(".result__title")
                    snippet_elem = result.select_one(".result__snippet")
                    link_elem = result.select_one("a.result__a")
                    if not link_elem:
                        link_elem = result.select_one("a[href*='http']")
                    if not title_elem:
                        title_elem = result.select_one("h2") or snippet_elem
                    if not title_elem or not link_elem:
                        continue
                    title = title_elem.get_text(strip=True)
                    snippet = (snippet_elem.get_text(strip=True) if snippet_elem else "") or ""
                    href = self._extract_href(link_elem.get("href", ""))
                    if not href.startswith("http"):
                        continue
                    results.append({"title": title, "snippet": snippet, "url": href})
                if results:
                    return results
                # Fallback: any link with snippet-like text (older DDG or regional variants)
                for block in soup.select("[class*='result']")[:max_results * 2]:
                    a = block.select_one("a[href^='http']") or block.select_one("a[href*='uddg=']")
                    if not a:
                        continue
                    href = self._extract_href(a.get("href", ""))
                    if not href.startswith("http"):
                        continue
                    title = (block.select_one("[class*='title']") or a).get_text(strip=True)
                    snip = (block.select_one("[class*='snippet']") or block).get_text(strip=True)
                    if title and len(title) > 3:
                        results.append({"title": title, "snippet": snip[:300], "url": href})
                        if len(results) >= max_results:
                            break
                return results
        except Exception as e:
            print(f"[DiscussionSearch] DDG error: {e}", flush=True)
        return []

    async def fetch(
        self,
        artist: str,
        track_title: str,
        album: str,
        track_id: str,
        **kwargs
    ) -> List[InfoCard]:
        variation = kwargs.get("variation", False)
        cards: List[InfoCard] = []
        seen_urls: set[str] = set()
        # Cap per-domain so we get variety (max 2 from Reddit, 2 from any other domain)
        domain_count: dict[str, int] = {}

        def _domain_key(url: str) -> str:
            try:
                host = urlparse(url).netloc.lower()
                return host.replace("www.", "") if host else "other"
            except Exception:
                return "other"

        # Run site-specific queries first so we get Quora, AOTY, etc.; then Reddit. Cap 2 per domain.
        if variation:
            queries = [
                f'"{artist}" "{track_title}" site:quora.com',
                f'"{artist}" "{album or track_title}" site:albumoftheyear.org',
                f'"{artist}" "{track_title}" site:music.stackexchange.com',
                f'"{artist}" "{track_title}" explained',
                f'"{artist}" "{album or track_title}" forum discussion',
                f'"{artist}" "{track_title}" site:reddit.com',
            ]
        else:
            queries = [
                f'"{artist}" "{track_title}" site:quora.com',
                f'"{artist}" "{track_title}" site:albumoftheyear.org',
                f'"{artist}" "{track_title}" site:music.stackexchange.com',
                f'"{artist}" "{track_title}" discussion',
                f'"{artist}" "{track_title}" meaning review',
                f'"{artist}" "{track_title}" site:reddit.com',
            ]
        if album:
            queries.append(f'"{artist}" "{album}" site:albumoftheyear.org')
            queries.append(f'"{artist}" "{album}" forum')

        max_cards = 6
        max_per_domain = 2

        for query in queries:
            if len(cards) >= max_cards:
                break
            results = await self._search_ddg_html(query, max_results=5)
            for r in results:
                if len(cards) >= max_cards:
                    break
                url = (r.get("url") or "").strip()
                if not url or url in seen_urls:
                    continue
                domain = _domain_key(url)
                if domain_count.get(domain, 0) >= max_per_domain:
                    continue
                seen_urls.add(url)
                domain_count[domain] = domain_count.get(domain, 0) + 1
                title = (r.get("title") or "").strip() or "Discussion"
                snippet = (r.get("snippet") or "").strip()
                # Only include if result is about this artist or track (avoid unrelated pages)
                combined_text = f"{title} {snippet}".lower()
                if artist.lower() not in combined_text and track_title.lower() not in combined_text:
                    if not album or album.lower() not in combined_text:
                        domain_count[domain] -= 1
                        seen_urls.discard(url)
                        continue
                label = _domain_label(url)
                display_title = f"{label}: {title}" if label != "Discussion" else title
                if len(display_title) > 100:
                    display_title = display_title[:97] + "..."
                summary = snippet[:400] if snippet else f"Discussion about {artist} — {track_title}."
                if len(snippet) > 400:
                    summary += "..."
                cards.append(
                    InfoCard(
                        id=str(uuid.uuid4()),
                        source=CardSource.DISCUSSION_SEARCH,
                        title=display_title,
                        summary=summary,
                        full_content=summary,
                        url=url,
                        track_id=track_id,
                        category="trivia",
                    )
                )
        print(f"[DiscussionSearch] Returning {len(cards)} cards (variation={variation})", flush=True)
        return cards
