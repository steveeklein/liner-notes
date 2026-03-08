from typing import List
import uuid
import os
import httpx

from app.models import InfoCard, CardSource
from .base import DataSource


class LastFmSource(DataSource):
    """Fetches data from Last.fm - similar artists, tags, listener stats."""
    
    BASE_URL = "https://ws.audioscrobbler.com/2.0/"
    
    def __init__(self):
        self.api_key = os.getenv("LASTFM_API_KEY")
    
    async def _get_track_info(self, artist: str, track: str) -> dict | None:
        """Get track info from Last.fm."""
        if not self.api_key:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "method": "track.getInfo",
                        "artist": artist,
                        "track": track,
                        "api_key": self.api_key,
                        "format": "json"
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.json().get("track")
        except Exception as e:
            print(f"Last.fm track error: {e}")
        return None
    
    async def _get_artist_info(self, artist: str) -> dict | None:
        """Get artist info from Last.fm."""
        if not self.api_key:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "method": "artist.getInfo",
                        "artist": artist,
                        "api_key": self.api_key,
                        "format": "json"
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.json().get("artist")
        except Exception as e:
            print(f"Last.fm artist error: {e}")
        return None
    
    async def _get_similar_artists(self, artist: str) -> List[dict]:
        """Get similar artists from Last.fm."""
        if not self.api_key:
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "method": "artist.getSimilar",
                        "artist": artist,
                        "api_key": self.api_key,
                        "format": "json",
                        "limit": 10
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("similarartists", {}).get("artist", [])
        except Exception as e:
            print(f"Last.fm similar error: {e}")
        return []
    
    async def _get_top_tags(self, artist: str) -> List[str]:
        """Get top tags for an artist."""
        if not self.api_key:
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    self.BASE_URL,
                    params={
                        "method": "artist.getTopTags",
                        "artist": artist,
                        "api_key": self.api_key,
                        "format": "json"
                    },
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    tags = data.get("toptags", {}).get("tag", [])
                    return [t["name"] for t in tags[:10]]
        except Exception as e:
            print(f"Last.fm tags error: {e}")
        return []
    
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
        
        track_info = await self._get_track_info(artist, track_title)
        if track_info:
            playcount = track_info.get("playcount", 0)
            listeners = track_info.get("listeners", 0)
            
            if playcount or listeners:
                cards.append(InfoCard(
                    id=str(uuid.uuid4()),
                    source=CardSource.LASTFM,
                    title="Listener Statistics",
                    summary=f"This track has been played {int(playcount):,} times by {int(listeners):,} listeners on Last.fm.",
                    url=track_info.get("url"),
                    track_id=track_id,
                    category="charts"
                ))
            
            wiki = track_info.get("wiki", {})
            if wiki.get("summary"):
                summary = wiki["summary"].split("<a href")[0].strip()
                cards.append(InfoCard(
                    id=str(uuid.uuid4()),
                    source=CardSource.LASTFM,
                    title=f"About '{track_title}'",
                    summary=summary[:400] + "..." if len(summary) > 400 else summary,
                    full_content=wiki.get("content"),
                    url=track_info.get("url"),
                    track_id=track_id,
                    category="song"
                ))
        
        similar = await self._get_similar_artists(artist)
        if similar:
            similar_names = [s["name"] for s in similar[:8]]
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.LASTFM,
                title=f"Similar to {artist}",
                summary=f"Listeners also enjoy: {', '.join(similar_names)}",
                track_id=track_id,
                category="similar"
            ))
        
        tags = await self._get_top_tags(artist)
        if tags:
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.LASTFM,
                title="Genre & Style Tags",
                summary=f"Tagged as: {', '.join(tags)}",
                track_id=track_id,
                category="genre"
            ))
        
        return cards
