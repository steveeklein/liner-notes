from typing import List
import uuid
import httpx
import asyncio

from app.models import InfoCard, CardSource
from .base import DataSource


class MusicBrainzSource(DataSource):
    """Fetches data from MusicBrainz - the open music encyclopedia."""
    
    BASE_URL = "https://musicbrainz.org/ws/2"
    
    def __init__(self):
        self.headers = {
            "User-Agent": "LinerNotes/1.0 (contact@example.com)",
            "Accept": "application/json"
        }
    
    async def _search_recording(self, artist: str, title: str) -> dict | None:
        """Search for a recording in MusicBrainz."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/recording",
                    params={
                        "query": f'recording:"{title}" AND artist:"{artist}"',
                        "fmt": "json",
                        "limit": 1
                    },
                    headers=self.headers,
                    timeout=10.0
                )
                await asyncio.sleep(1)
                
                if response.status_code == 200:
                    data = response.json()
                    recordings = data.get("recordings", [])
                    if recordings:
                        return recordings[0]
        except Exception as e:
            print(f"MusicBrainz search error: {e}")
        return None
    
    async def _get_artist_details(self, artist_id: str) -> dict | None:
        """Get detailed artist info."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/artist/{artist_id}",
                    params={
                        "inc": "url-rels+artist-rels+tags+ratings",
                        "fmt": "json"
                    },
                    headers=self.headers,
                    timeout=10.0
                )
                await asyncio.sleep(1)
                
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"MusicBrainz artist error: {e}")
        return None
    
    async def _get_recording_details(self, recording_id: str) -> dict | None:
        """Get detailed recording info including credits."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/recording/{recording_id}",
                    params={
                        "inc": "artist-credits+work-rels+artist-rels+releases+tags",
                        "fmt": "json"
                    },
                    headers=self.headers,
                    timeout=10.0
                )
                await asyncio.sleep(1)
                
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"MusicBrainz recording error: {e}")
        return None
    
    async def fetch(
        self,
        artist: str,
        track_title: str,
        album: str,
        track_id: str
    ) -> List[InfoCard]:
        cards = []
        
        recording = await self._search_recording(artist, track_title)
        if not recording:
            return cards
        
        recording_id = recording.get("id")
        if recording_id:
            details = await self._get_recording_details(recording_id)
            if details:
                artist_credits = details.get("artist-credit", [])
                if len(artist_credits) > 1:
                    performers = [ac.get("name") for ac in artist_credits if ac.get("name")]
                    cards.append(InfoCard(
                        id=str(uuid.uuid4()),
                        source=CardSource.MUSICBRAINZ,
                        title="Featured Artists",
                        summary=f"Performed by: {', '.join(performers)}",
                        url=f"https://musicbrainz.org/recording/{recording_id}",
                        track_id=track_id,
                        category="credits"
                    ))
                
                relations = details.get("relations", [])
                writers = []
                producers = []
                for rel in relations:
                    rel_type = rel.get("type", "")
                    if rel_type in ["writer", "composer", "lyricist"]:
                        artist_info = rel.get("artist", {})
                        if artist_info.get("name"):
                            writers.append(f"{artist_info['name']} ({rel_type})")
                    elif rel_type == "producer":
                        artist_info = rel.get("artist", {})
                        if artist_info.get("name"):
                            producers.append(artist_info["name"])
                
                if writers:
                    cards.append(InfoCard(
                        id=str(uuid.uuid4()),
                        source=CardSource.MUSICBRAINZ,
                        title="Songwriting Credits",
                        summary=f"Written by: {', '.join(writers[:5])}",
                        url=f"https://musicbrainz.org/recording/{recording_id}",
                        track_id=track_id,
                        category="credits"
                    ))
                
                if producers:
                    cards.append(InfoCard(
                        id=str(uuid.uuid4()),
                        source=CardSource.MUSICBRAINZ,
                        title="Production Credits",
                        summary=f"Produced by: {', '.join(producers[:5])}",
                        url=f"https://musicbrainz.org/recording/{recording_id}",
                        track_id=track_id,
                        category="credits"
                    ))
                
                tags = details.get("tags", [])
                if tags:
                    tag_names = [t["name"] for t in sorted(tags, key=lambda x: x.get("count", 0), reverse=True)[:8]]
                    cards.append(InfoCard(
                        id=str(uuid.uuid4()),
                        source=CardSource.MUSICBRAINZ,
                        title="Community Tags",
                        summary=f"Tagged as: {', '.join(tag_names)}",
                        url=f"https://musicbrainz.org/recording/{recording_id}",
                        track_id=track_id,
                        category="genre"
                    ))
        
        first_release = recording.get("first-release-date")
        if first_release:
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.MUSICBRAINZ,
                title="Release Date",
                summary=f"First released: {first_release}",
                track_id=track_id,
                category="history"
            ))
        
        return cards
