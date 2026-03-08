from typing import List
import uuid
import os
import httpx

from app.models import InfoCard, CardSource
from .base import DataSource


class DiscogsSource(DataSource):
    """Fetches data from Discogs - vinyl releases, credits, labels."""
    
    BASE_URL = "https://api.discogs.com"
    
    def __init__(self):
        self.token = os.getenv("DISCOGS_TOKEN")
        self.headers = {
            "User-Agent": "LinerNotes/1.0",
        }
        if self.token:
            self.headers["Authorization"] = f"Discogs token={self.token}"
    
    async def _search(self, artist: str, track: str = None, album: str = None) -> dict | None:
        """Search Discogs database."""
        try:
            query = artist
            if track:
                query += f" {track}"
            elif album:
                query += f" {album}"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/database/search",
                    params={
                        "q": query,
                        "type": "release" if album else "master",
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
            print(f"Discogs search error: {e}")
        return None
    
    async def _get_release_details(self, release_url: str) -> dict | None:
        """Get detailed release information."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    release_url,
                    headers=self.headers,
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"Discogs release error: {e}")
        return None
    
    async def _get_artist_details(self, artist_id: int) -> dict | None:
        """Get detailed artist information."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/artists/{artist_id}",
                    headers=self.headers,
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"Discogs artist error: {e}")
        return None
    
    async def fetch(
        self,
        artist: str,
        track_title: str,
        album: str,
        track_id: str
    ) -> List[InfoCard]:
        cards = []
        
        result = await self._search(artist, album=album)
        if not result:
            result = await self._search(artist, track=track_title)
        
        if not result:
            return cards
        
        release_url = result.get("resource_url")
        if release_url:
            details = await self._get_release_details(release_url)
            if details:
                labels = details.get("labels", [])
                if labels:
                    label_info = labels[0]
                    catno = label_info.get("catno", "")
                    label_name = label_info.get("name", "")
                    cards.append(InfoCard(
                        id=str(uuid.uuid4()),
                        source=CardSource.DISCOGS,
                        title="Label & Catalog",
                        summary=f"Released on {label_name}" + (f" (Catalog: {catno})" if catno else ""),
                        url=result.get("uri"),
                        track_id=track_id,
                        category="album"
                    ))
                
                formats = details.get("formats", [])
                if formats:
                    format_names = [f.get("name", "") for f in formats]
                    format_text = ", ".join(set(format_names))
                    cards.append(InfoCard(
                        id=str(uuid.uuid4()),
                        source=CardSource.DISCOGS,
                        title="Available Formats",
                        summary=f"Released on: {format_text}",
                        url=result.get("uri"),
                        track_id=track_id,
                        category="album"
                    ))
                
                credits = details.get("extraartists", [])
                if credits:
                    credit_lines = []
                    for credit in credits[:8]:
                        name = credit.get("name", "")
                        role = credit.get("role", "")
                        if name and role:
                            credit_lines.append(f"{name} ({role})")
                    
                    if credit_lines:
                        cards.append(InfoCard(
                            id=str(uuid.uuid4()),
                            source=CardSource.DISCOGS,
                            title="Recording Credits",
                            summary=", ".join(credit_lines),
                            url=result.get("uri"),
                            track_id=track_id,
                            category="credits"
                        ))
                
                notes = details.get("notes")
                if notes:
                    cards.append(InfoCard(
                        id=str(uuid.uuid4()),
                        source=CardSource.DISCOGS,
                        title="Release Notes",
                        summary=notes[:400] + "..." if len(notes) > 400 else notes,
                        full_content=notes,
                        url=result.get("uri"),
                        track_id=track_id,
                        category="album"
                    ))
        
        genres = result.get("genre", [])
        styles = result.get("style", [])
        if genres or styles:
            all_tags = genres + styles
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.DISCOGS,
                title="Genres & Styles",
                summary=", ".join(all_tags[:10]),
                url=result.get("uri"),
                track_id=track_id,
                category="genre"
            ))
        
        return cards
