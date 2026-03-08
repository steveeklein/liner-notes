from typing import List
import uuid
import os
import re
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
                                "id": result.get("id"),
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
                                    "id": result.get("id"),
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
                        lyrics_preview = lyrics_text[:800] + "..." if len(lyrics_text) > 800 else lyrics_text
                    
                    return {
                        "about": about_text,
                        "lyrics_preview": lyrics_preview
                    }
        except Exception as e:
            print(f"Genius scrape error: {e}")
        
        return None
    
    async def _get_annotations(self, song_id: int, url: str) -> List[dict]:
        """Fetch actual annotation content from Genius."""
        annotations = []
        
        try:
            referents_url = f"https://genius.com/api/referents?song_id={song_id}&per_page=10&text_format=plain"
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(referents_url, headers=self.headers, timeout=10.0)
                if response.status_code == 200:
                    data = response.json()
                    referents = data.get("response", {}).get("referents", [])
                    
                    for ref in referents[:8]:
                        fragment = ref.get("fragment", "")
                        annotation_list = ref.get("annotations", [])
                        
                        if annotation_list:
                            annotation = annotation_list[0]
                            body = annotation.get("body", {})
                            
                            if isinstance(body, dict):
                                annotation_text = body.get("plain", "")
                            else:
                                annotation_text = str(body) if body else ""
                            
                            if annotation_text and len(annotation_text) > 20:
                                fragment_clean = fragment.strip()[:100]
                                if len(fragment) > 100:
                                    fragment_clean += "..."
                                
                                annotations.append({
                                    "lyric": fragment_clean,
                                    "explanation": annotation_text.strip(),
                                    "votes": annotation.get("votes_total", 0)
                                })
        except Exception as e:
            print(f"Genius annotations API error: {e}")
        
        if not annotations:
            try:
                async with httpx.AsyncClient(follow_redirects=True) as client:
                    response = await client.get(url, headers=self.headers, timeout=15.0)
                    if response.status_code == 200:
                        soup = BeautifulSoup(response.text, 'html.parser')
                        
                        annotation_elems = soup.select('[class*="Annotation"]')
                        for elem in annotation_elems[:5]:
                            text = elem.get_text(strip=True)
                            if text and len(text) > 30:
                                annotations.append({
                                    "lyric": "",
                                    "explanation": text[:500],
                                    "votes": 0
                                })
            except Exception as e:
                print(f"Genius annotation scrape error: {e}")
        
        return annotations
    
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
            about_text = details["about"]
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.GENIUS,
                title=f"About '{track_title}'",
                summary=about_text[:800] + "..." if len(about_text) > 800 else about_text,
                full_content=about_text if len(about_text) > 800 else None,
                url=song["url"],
                image_url=song.get("image_url"),
                track_id=track_id,
                category="song"
            ))
        
        if details and details.get("lyrics_preview"):
            lyrics = details["lyrics_preview"]
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.GENIUS,
                title=f"Lyrics Preview",
                summary=lyrics[:600] if len(lyrics) > 600 else lyrics,
                full_content=lyrics if len(lyrics) > 600 else None,
                url=song["url"],
                track_id=track_id,
                category="lyrics"
            ))
        
        if song.get("annotation_count", 0) > 0 and song.get("id"):
            annotations = await self._get_annotations(song["id"], song["url"])
            
            if annotations:
                formatted_annotations = []
                for i, ann in enumerate(annotations[:5], 1):
                    lyric = ann.get("lyric", "")
                    explanation = ann.get("explanation", "")
                    
                    if lyric and explanation:
                        formatted_annotations.append(
                            f'"{lyric}"\n{explanation}'
                        )
                    elif explanation:
                        formatted_annotations.append(explanation)
                
                if formatted_annotations:
                    summary_text = formatted_annotations[0]
                    if len(summary_text) > 400:
                        summary_text = summary_text[:400] + "..."
                    
                    full_content = "\n\n---\n\n".join(formatted_annotations)
                    
                    cards.append(InfoCard(
                        id=str(uuid.uuid4()),
                        source=CardSource.GENIUS,
                        title="Community Insights",
                        summary=summary_text,
                        full_content=full_content if len(formatted_annotations) > 1 else None,
                        url=song["url"],
                        track_id=track_id,
                        category="lyrics"
                    ))
        
        return cards
