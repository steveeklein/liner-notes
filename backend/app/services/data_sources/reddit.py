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
        
        song_posts = await self._search_reddit(f'"{artist}" "{track_title}"')
        
        relevant_posts = []
        for post in song_posts:
            subreddit = post.get("subreddit", "")
            if subreddit.lower() in [s.lower() for s in self.music_subreddits]:
                relevant_posts.append(post)
        
        if relevant_posts:
            post = relevant_posts[0]
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.REDDIT,
                title=f"Discussion: {post.get('title', '')[:60]}...",
                summary=f"r/{post.get('subreddit')} • {post.get('score', 0)} upvotes • {post.get('num_comments', 0)} comments",
                url=f"https://reddit.com{post.get('permalink', '')}",
                track_id=track_id,
                category="trivia"
            ))
        
        artist_sub = await self._get_artist_subreddit(artist)
        if artist_sub:
            sub_posts = await self._search_reddit(track_title, subreddit=artist_sub)
            if sub_posts:
                post = sub_posts[0]
                cards.append(InfoCard(
                    id=str(uuid.uuid4()),
                    source=CardSource.REDDIT,
                    title=f"r/{artist_sub}: {post.get('title', '')[:50]}",
                    summary=f"From the {artist} fan community • {post.get('num_comments', 0)} comments",
                    url=f"https://reddit.com{post.get('permalink', '')}",
                    track_id=track_id,
                    category="trivia"
                ))
        
        letstalk_posts = await self._search_reddit(f'"{artist}"', subreddit="LetsTalkMusic")
        for post in letstalk_posts[:1]:
            if post.get("score", 0) > 10:
                cards.append(InfoCard(
                    id=str(uuid.uuid4()),
                    source=CardSource.REDDIT,
                    title="Music Analysis Discussion",
                    summary=f"{post.get('title', '')[:100]}",
                    url=f"https://reddit.com{post.get('permalink', '')}",
                    track_id=track_id,
                    category="trivia"
                ))
        
        return cards
