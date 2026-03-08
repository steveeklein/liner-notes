from typing import List
import uuid
import os
import httpx
from bs4 import BeautifulSoup

from app.models import InfoCard, CardSource
from .base import DataSource


class GeniusSource(DataSource):
    """Fetches lyrics and annotations from Genius."""
    
    BASE_URL = "https://api.genius.com"
    
    def __init__(self):
        self.access_token = os.getenv("GENIUS_ACCESS_TOKEN")
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
        }
    
    async def _search_song(self, artist: str, title: str) -> dict | None:
        """Search for a song on Genius."""
        query = f"{artist} {title}"
        
        if self.access_token:
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        f"{self.BASE_URL}/search",
                        params={"q": query},
                        headers={"Authorization": f"Bearer {self.access_token}"},
                        timeout=10.0
                    )
                    if response.status_code == 200:
                        data = response.json()
                        hits = data.get("response", {}).get("hits", [])
                        if hits:
                            result = hits[0].get("result", {})
                            return {
                                "title": result.get("title"),
                                "artist": result.get("primary_artist", {}).get("name"),
                                "url": result.get("url"),
                                "lyrics_path": result.get("path"),
                                "annotation_count": result.get("annotation_count", 0),
                                "image_url": result.get("song_art_image_url")
                            }
            except Exception as e:
                print(f"Genius API error: {e}")
        
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                search_url = f"https://genius.com/api/search/multi?q={query.replace(' ', '%20')}"
                response = await client.get(search_url, headers=self.headers, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    sections = data.get("response", {}).get("sections", [])
                    for section in sections:
                        if section.get("type") == "song":
                            hits = section.get("hits", [])
                            if hits:
                                result = hits[0].get("result", {})
                                return {
                                    "title": result.get("title"),
                                    "artist": result.get("primary_artist", {}).get("name"),
                                    "url": result.get("url"),
                                    "annotation_count": result.get("annotation_count", 0),
                                    "image_url": result.get("song_art_image_url")
                                }
        except Exception as e:
            print(f"Genius search error: {e}")
        
        return None
    
    async def _get_song_details(self, url: str) -> dict | None:
        """Scrape additional song details from Genius page."""
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers, timeout=15.0)
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    about_elem = soup.select_one('[class*="SongDescription"]')
                    about_text = about_elem.get_text(strip=True) if about_elem else None
                    
                    lyrics_elem = soup.select_one('[data-lyrics-container="true"]')
                    lyrics_preview = None
                    if lyrics_elem:
                        lyrics_text = lyrics_elem.get_text('\n', strip=True)
                        lyrics_preview = lyrics_text[:300] + "..." if len(lyrics_text) > 300 else lyrics_text
                    
                    return {
                        "about": about_text,
                        "lyrics_preview": lyrics_preview
                    }
        except Exception as e:
            print(f"Genius scrape error: {e}")
        
        return None
    
    async def fetch(
        self,
        artist: str,
        track_title: str,
        album: str,
        track_id: str
    ) -> List[InfoCard]:
        cards = []
        
        song = await self._search_song(artist, track_title)
        if not song:
            return cards
        
        details = await self._get_song_details(song["url"]) if song.get("url") else None
        
        if details and details.get("about"):
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.GENIUS,
                title=f"About '{track_title}'",
                summary=details["about"][:400] + "..." if len(details["about"]) > 400 else details["about"],
                full_content=details["about"],
                url=song["url"],
                image_url=song.get("image_url"),
                track_id=track_id,
                category="song"
            ))
        
        if details and details.get("lyrics_preview"):
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.GENIUS,
                title=f"Lyrics: {track_title}",
                summary=details["lyrics_preview"],
                url=song["url"],
                track_id=track_id,
                category="lyrics"
            ))
        
        if song.get("annotation_count", 0) > 0:
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.GENIUS,
                title="Community Annotations",
                summary=f"This song has {song['annotation_count']} annotations from the Genius community explaining lyrics and references.",
                url=song["url"],
                track_id=track_id,
                category="lyrics"
            ))
        
        return cards
