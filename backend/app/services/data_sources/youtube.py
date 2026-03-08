from typing import List
import uuid
import os
import httpx

from app.models import InfoCard, CardSource
from .base import DataSource


class YouTubeSource(DataSource):
    """Fetches music videos, interviews, and live performances from YouTube."""
    
    BASE_URL = "https://www.googleapis.com/youtube/v3"
    
    def __init__(self):
        self.api_key = os.getenv("YOUTUBE_API_KEY")
    
    async def _search_videos(self, query: str, video_type: str = None) -> List[dict]:
        """Search for videos on YouTube."""
        if not self.api_key:
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/search",
                    params={
                        "part": "snippet",
                        "q": query,
                        "type": "video",
                        "maxResults": 5,
                        "key": self.api_key,
                        "videoCategoryId": "10"  # Music category
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("items", [])
        except Exception as e:
            print(f"YouTube search error: {e}")
        return []
    
    async def _get_video_details(self, video_id: str) -> dict | None:
        """Get detailed video information."""
        if not self.api_key:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/videos",
                    params={
                        "part": "snippet,statistics,contentDetails",
                        "id": video_id,
                        "key": self.api_key
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    items = data.get("items", [])
                    if items:
                        return items[0]
        except Exception as e:
            print(f"YouTube video details error: {e}")
        return None
    
    async def fetch(
        self,
        artist: str,
        track_title: str,
        album: str,
        track_id: str
    ) -> List[InfoCard]:
        cards = []
        
        if not self.api_key:
            return cards
        
        official_results = await self._search_videos(f"{artist} {track_title} official music video")
        if official_results:
            video = official_results[0]
            snippet = video.get("snippet", {})
            video_id = video.get("id", {}).get("videoId")
            
            if video_id:
                details = await self._get_video_details(video_id)
                view_count = ""
                if details:
                    stats = details.get("statistics", {})
                    views = int(stats.get("viewCount", 0))
                    if views > 0:
                        view_count = f" ({views:,} views)"
                
                cards.append(InfoCard(
                    id=str(uuid.uuid4()),
                    source=CardSource.YOUTUBE,
                    title="Official Music Video",
                    summary=f"{snippet.get('title', track_title)}{view_count}",
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    image_url=snippet.get("thumbnails", {}).get("high", {}).get("url"),
                    track_id=track_id,
                    category="videos"
                ))
        
        live_results = await self._search_videos(f"{artist} {track_title} live performance")
        for video in live_results[:2]:
            snippet = video.get("snippet", {})
            video_id = video.get("id", {}).get("videoId")
            title = snippet.get("title", "")
            
            if video_id and "live" in title.lower():
                cards.append(InfoCard(
                    id=str(uuid.uuid4()),
                    source=CardSource.YOUTUBE,
                    title="Live Performance",
                    summary=title,
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    image_url=snippet.get("thumbnails", {}).get("medium", {}).get("url"),
                    track_id=track_id,
                    category="videos"
                ))
                break
        
        interview_results = await self._search_videos(f"{artist} interview {track_title} OR {album}")
        for video in interview_results[:2]:
            snippet = video.get("snippet", {})
            video_id = video.get("id", {}).get("videoId")
            title = snippet.get("title", "")
            
            if video_id and ("interview" in title.lower() or "behind" in title.lower()):
                cards.append(InfoCard(
                    id=str(uuid.uuid4()),
                    source=CardSource.YOUTUBE,
                    title="Artist Interview",
                    summary=title,
                    url=f"https://www.youtube.com/watch?v={video_id}",
                    image_url=snippet.get("thumbnails", {}).get("medium", {}).get("url"),
                    track_id=track_id,
                    category="videos"
                ))
                break
        
        return cards
