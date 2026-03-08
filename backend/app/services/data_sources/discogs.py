from typing import List
import uuid
import httpx

from app.models import InfoCard, CardSource
from .base import DataSource


class DiscogsSource(DataSource):
    """Fetches release info and credits from Discogs public API."""
    
    BASE_URL = "https://api.discogs.com"
    
    def __init__(self):
        self.headers = {
            "User-Agent": "LinerNotes/1.0"
        }
    
    async def _search_release(self, artist: str, title: str) -> dict | None:
        """Search for a release on Discogs."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/database/search",
                    params={
                        "q": f"{artist} {title}",
                        "type": "release",
                        "per_page": 5
                    },
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    if results:
                        return results[0]
        except Exception as e:
            print(f"Discogs search error: {e}", flush=True)
        return None
    
    async def _search_artist(self, artist: str) -> dict | None:
        """Search for an artist on Discogs."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/database/search",
                    params={
                        "q": artist,
                        "type": "artist",
                        "per_page": 1
                    },
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    if results:
                        return results[0]
        except Exception as e:
            print(f"Discogs artist search error: {e}", flush=True)
        return None
    
    async def _get_release_details(self, release_id: int) -> dict | None:
        """Get detailed release info."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/releases/{release_id}",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"Discogs release details error: {e}", flush=True)
        return None
    
    async def fetch(
        self,
        artist: str,
        track_title: str,
        album: str,
        track_id: str
    ) -> List[InfoCard]:
        cards = []
        
        # Search for the release
        release = await self._search_release(artist, track_title)
        if release:
            release_url = f"https://www.discogs.com/release/{release.get('id', '')}"
            
            # Basic release info card
            title_text = release.get("title", "")
            year = release.get("year", "")
            label = release.get("label", ["Unknown label"])[0] if release.get("label") else ""
            format_info = release.get("format", [""])[0] if release.get("format") else ""
            
            summary_parts = []
            if year:
                summary_parts.append(f"Released: {year}")
            if label:
                summary_parts.append(f"Label: {label}")
            if format_info:
                summary_parts.append(f"Format: {format_info}")
            
            if summary_parts:
                cards.append(InfoCard(
                    id=str(uuid.uuid4()),
                    source=CardSource.DISCOGS,
                    title="Release Information",
                    summary=" • ".join(summary_parts),
                    url=release_url,
                    track_id=track_id,
                    category="credits"
                ))
            
            # Get genres/styles
            genres = release.get("genre", [])
            styles = release.get("style", [])
            
            if genres or styles:
                genre_text = ""
                if genres:
                    genre_text += f"Genre: {', '.join(genres[:3])}"
                if styles:
                    if genre_text:
                        genre_text += " | "
                    genre_text += f"Style: {', '.join(styles[:4])}"
                
                cards.append(InfoCard(
                    id=str(uuid.uuid4()),
                    source=CardSource.DISCOGS,
                    title="Genre Classification",
                    summary=genre_text,
                    url=release_url,
                    track_id=track_id,
                    category="genre"
                ))
        
        # Search for artist info  
        artist_result = await self._search_artist(artist)
        if artist_result:
            artist_url = f"https://www.discogs.com/artist/{artist_result.get('id', '')}"
            
            # If we have artist info
            if artist_result.get("title"):
                cards.append(InfoCard(
                    id=str(uuid.uuid4()),
                    source=CardSource.DISCOGS,
                    title=f"Discography",
                    summary=f"Explore {artist}'s full discography on Discogs",
                    url=artist_url,
                    track_id=track_id,
                    category="artist"
                ))
        
        return cards
