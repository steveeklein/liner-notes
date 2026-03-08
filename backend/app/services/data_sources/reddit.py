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
    
    async def _search_reddit(self, query: str, subreddit: str = None) -> List[dict]:
        """Search Reddit for discussions."""
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
                        "sort": "relevance",
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
        track_id: str
    ) -> List[InfoCard]:
        cards = []
        
        # Try multiple search strategies
        search_queries = [
            f'{artist} {track_title}',
            f'{artist}',
        ]
        
        for query in search_queries:
            if len(cards) >= 2:
                break
                
            posts = await self._search_reddit(query)
            
            for post in posts:
                if len(cards) >= 2:
                    break
                    
                subreddit = post.get("subreddit", "").lower()
                score = post.get("score", 0)
                title = post.get("title", "")
                
                # Check if it's from a music subreddit and has decent engagement
                is_music_sub = subreddit in [s.lower() for s in self.music_subreddits]
                
                if is_music_sub and score >= 5 and len(title) > 10:
                    # Avoid duplicate titles
                    existing_titles = [c.title for c in cards]
                    short_title = title[:60] + "..." if len(title) > 60 else title
                    
                    if short_title not in existing_titles:
                        cards.append(InfoCard(
                            id=str(uuid.uuid4()),
                            source=CardSource.REDDIT,
                            title=short_title,
                            summary=f"r/{post.get('subreddit')} • {score} upvotes • {post.get('num_comments', 0)} comments",
                            url=f"https://reddit.com{post.get('permalink', '')}",
                            track_id=track_id,
                            category="trivia"
                        ))
        
        return cards
