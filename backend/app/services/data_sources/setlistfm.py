from typing import List
import uuid
import os
import httpx

from app.models import InfoCard, CardSource
from .base import DataSource


class SetlistFmSource(DataSource):
    """Fetches concert setlist data from setlist.fm."""
    
    BASE_URL = "https://api.setlist.fm/rest/1.0"
    
    def __init__(self):
        self.api_key = os.getenv("SETLISTFM_API_KEY")
        self.headers = {
            "Accept": "application/json",
        }
        if self.api_key:
            self.headers["x-api-key"] = self.api_key
    
    async def _search_artist(self, artist: str) -> dict | None:
        """Search for an artist."""
        if not self.api_key:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/search/artists",
                    params={"artistName": artist, "sort": "relevance"},
                    headers=self.headers,
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    artists = data.get("artist", [])
                    if artists:
                        return artists[0]
        except Exception as e:
            print(f"Setlist.fm search error: {e}")
        return None
    
    async def _get_setlists(self, artist_mbid: str) -> List[dict]:
        """Get recent setlists for an artist."""
        if not self.api_key:
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/artist/{artist_mbid}/setlists",
                    params={"p": 1},
                    headers=self.headers,
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("setlist", [])[:5]
        except Exception as e:
            print(f"Setlist.fm setlists error: {e}")
        return []
    
    async def _search_song_in_setlists(self, setlists: List[dict], track_title: str) -> dict | None:
        """Find when a song was played in setlists."""
        track_lower = track_title.lower()
        
        for setlist in setlists:
            sets = setlist.get("sets", {}).get("set", [])
            for set_data in sets:
                songs = set_data.get("song", [])
                for song in songs:
                    if track_lower in song.get("name", "").lower():
                        venue = setlist.get("venue", {})
                        return {
                            "date": setlist.get("eventDate"),
                            "venue": venue.get("name"),
                            "city": venue.get("city", {}).get("name"),
                            "country": venue.get("city", {}).get("country", {}).get("name"),
                            "url": setlist.get("url")
                        }
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
        
        artist_data = await self._search_artist(artist)
        if not artist_data:
            return cards
        
        mbid = artist_data.get("mbid")
        if not mbid:
            return cards
        
        setlists = await self._get_setlists(mbid)
        
        if setlists:
            recent = setlists[0]
            venue = recent.get("venue", {})
            city = venue.get("city", {})
            
            concert_info = f"{venue.get('name', 'Unknown venue')}, {city.get('name', '')}, {city.get('country', {}).get('name', '')}"
            date = recent.get("eventDate", "")
            
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.SETLISTFM,
                title=f"Recent Concert",
                summary=f"{artist} recently performed at {concert_info} on {date}",
                url=recent.get("url"),
                track_id=track_id,
                category="concerts"
            ))
        
        song_performance = await self._search_song_in_setlists(setlists, track_title)
        if song_performance:
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.SETLISTFM,
                title=f"'{track_title}' Live",
                summary=f"Recently performed at {song_performance['venue']}, {song_performance['city']} ({song_performance['date']})",
                url=song_performance.get("url"),
                track_id=track_id,
                category="concerts"
            ))
        
        return cards
