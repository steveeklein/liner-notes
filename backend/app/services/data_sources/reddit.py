from typing import List
import uuid
import httpx

from app.models import InfoCard, CardSource
from .base import DataSource


class RedditSource(DataSource):
    """Fetches discussions from music subreddits."""
    
    def __init__(self):
        self.headers = {
            "User-Agent": "LinerNotes/1.0"
        }
        self.music_subreddits = [
            "Music", "listentothis", "LetsTalkMusic", "indieheads",
            "hiphopheads", "electronicmusic", "Metal", "Jazz",
            "WeAreTheMusicMakers", "musictheory"
        ]
    
    async def _search_reddit(self, query: str, subreddit: str = None, sort: str = "relevance") -> List[dict]:
        """Search Reddit for discussions. sort: relevance, new, hot, top, comments."""
        try:
            if subreddit:
                url = f"https://www.reddit.com/r/{subreddit}/search.json"
            else:
                url = "https://www.reddit.com/search.json"
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    params={
                        "q": query,
                        "sort": sort,
                        "limit": 10,
                        "restrict_sr": "true" if subreddit else "false"
                    },
                    headers=self.headers,
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    posts = data.get("data", {}).get("children", [])
                    return [p.get("data", {}) for p in posts]
        except Exception as e:
            print(f"Reddit search error: {e}")
        return []
    
    async def _get_artist_subreddit(self, artist: str) -> str | None:
        """Check if artist has a dedicated subreddit."""
        try:
            subreddit_name = artist.replace(" ", "").replace("-", "")
            url = f"https://www.reddit.com/r/{subreddit_name}/about.json"
            
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers, timeout=5.0)
                if response.status_code == 200:
                    data = response.json()
                    if data.get("data", {}).get("subscribers", 0) > 1000:
                        return subreddit_name
        except Exception:
            pass
        return None
    
    async def fetch(
        self,
        artist: str,
        track_title: str,
        album: str,
        track_id: str,
        **kwargs
    ) -> List[InfoCard]:
        variation = kwargs.get("variation", False)
        sort = "new" if variation else "relevance"
        cards = []

        # Prefer artist-specific subreddit first (e.g. r/radiohead), then global search
        artist_sub = await self._get_artist_subreddit(artist)
        to_try = []
        if artist_sub:
            to_try.append((f'{artist} {track_title}', artist_sub))
        to_try.append((f'{artist} {track_title}', None))
        to_try.append((artist, None))

        for query, subreddit in to_try:
            if len(cards) >= 4:
                break
            posts = await self._search_reddit(query, subreddit=subreddit, sort=sort)
            for post in posts:
                if len(cards) >= 4:
                    break
                subreddit_name = (post.get("subreddit") or "").lower()
                score = post.get("score", 0)
                title = (post.get("title") or "").strip()
                selftext_raw = (post.get("selftext") or "").strip()
                if len(title) < 5:
                    continue
                # Require post to be about this artist/track: title or selftext must mention artist or track (or album)
                combined = f"{title} {selftext_raw}".lower()
                artist_lower = artist.lower()
                track_lower = track_title.lower()
                album_lower = (album or "").lower()
                if artist_lower and artist_lower not in combined:
                    continue
                if track_lower and album_lower and track_lower not in combined and album_lower not in combined:
                    # Prefer posts that mention the track or album when we have both
                    pass  # still allow if artist is in
                # Accept: music subreddits with score >= 3, or any subreddit with score >= 5, or artist subreddit with score >= 1
                is_music_sub = subreddit_name in [s.lower() for s in self.music_subreddits]
                is_artist_sub = artist_sub and subreddit_name == artist_sub.lower()
                if not (is_music_sub and score >= 3) and not (score >= 5) and not (is_artist_sub and score >= 1):
                    continue
                existing_titles = [c.title for c in cards]
                short_title = title[:60] + "..." if len(title) > 60 else title
                if short_title in existing_titles:
                    continue
                selftext = selftext_raw
                meta = f"r/{post.get('subreddit')} · {score} upvotes · {post.get('num_comments', 0)} comments"
                if selftext:
                    summary = selftext[:400].rstrip()
                    if len(selftext) > 400:
                        summary += "..."
                    summary = f"{meta}\n\n{summary}"
                    full_content = f"{meta}\n\n{selftext}"
                else:
                    summary = meta
                    full_content = meta
                cards.append(InfoCard(
                    id=str(uuid.uuid4()),
                    source=CardSource.REDDIT,
                    title=short_title,
                    summary=summary,
                    full_content=full_content,
                    url=f"https://reddit.com{post.get('permalink', '')}",
                    track_id=track_id,
                    category="trivia"
                ))
        return cards
