from typing import List
import uuid
import httpx
from bs4 import BeautifulSoup

from app.models import InfoCard, CardSource
from .base import DataSource


class WhoSampledSource(DataSource):
    """Fetches sample information from WhoSampled."""
    
    BASE_URL = "https://www.whosampled.com"
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
    
    def _normalize_for_url(self, text: str) -> str:
        """Normalize text for URL path."""
        return text.replace(" ", "-").replace("'", "").replace(".", "").replace(",", "")
    
    async def _get_song_page(self, artist: str, title: str) -> dict | None:
        """Get WhoSampled page for a song."""
        try:
            artist_url = self._normalize_for_url(artist)
            title_url = self._normalize_for_url(title)
            url = f"{self.BASE_URL}/{artist_url}/{title_url}/"
            
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers, timeout=15.0)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    result = {"url": str(response.url)}
                    
                    samples_section = soup.select_one('.sampleSection')
                    if samples_section:
                        samples = []
                        for entry in samples_section.select('.listEntry')[:5]:
                            sample_track = entry.select_one('.trackName')
                            sample_artist = entry.select_one('.trackArtist')
                            if sample_track and sample_artist:
                                samples.append({
                                    "track": sample_track.get_text(strip=True),
                                    "artist": sample_artist.get_text(strip=True)
                                })
                        if samples:
                            result["samples"] = samples
                    
                    sampled_by_section = soup.select('.sampleEntry')
                    sampled_by = []
                    for entry in sampled_by_section[:5]:
                        track_elem = entry.select_one('.trackName')
                        artist_elem = entry.select_one('.trackArtist')
                        if track_elem and artist_elem:
                            sampled_by.append({
                                "track": track_elem.get_text(strip=True),
                                "artist": artist_elem.get_text(strip=True)
                            })
                    if sampled_by:
                        result["sampled_by"] = sampled_by
                    
                    covers_section = soup.select_one('[id*="cover"]')
                    if covers_section:
                        covers = []
                        for entry in covers_section.select('.listEntry')[:5]:
                            track_elem = entry.select_one('.trackName')
                            artist_elem = entry.select_one('.trackArtist')
                            if track_elem and artist_elem:
                                covers.append({
                                    "track": track_elem.get_text(strip=True),
                                    "artist": artist_elem.get_text(strip=True)
                                })
                        if covers:
                            result["covers"] = covers
                    
                    return result if len(result) > 1 else None
        except Exception as e:
            print(f"WhoSampled error: {e}")
        
        return None
    
    async def fetch(
        self,
        artist: str,
        track_title: str,
        album: str,
        track_id: str
    ) -> List[InfoCard]:
        cards = []
        
        data = await self._get_song_page(artist, track_title)
        if not data:
            return cards
        
        url = data.get("url", "")
        
        samples = data.get("samples", [])
        if samples:
            sample_text = ", ".join([f'"{s["track"]}" by {s["artist"]}' for s in samples[:3]])
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.WHOSAMPLED,
                title="Samples Used",
                summary=f"This track samples: {sample_text}",
                url=url,
                track_id=track_id,
                category="samples"
            ))
        
        sampled_by = data.get("sampled_by", [])
        if sampled_by:
            sampled_text = ", ".join([f'"{s["track"]}" by {s["artist"]}' for s in sampled_by[:3]])
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.WHOSAMPLED,
                title="Sampled By",
                summary=f"This track has been sampled in: {sampled_text}",
                url=url,
                track_id=track_id,
                category="samples"
            ))
        
        covers = data.get("covers", [])
        if covers:
            cover_text = ", ".join([f'{c["artist"]}' for c in covers[:5]])
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.WHOSAMPLED,
                title="Cover Versions",
                summary=f"Covered by: {cover_text}",
                url=url,
                track_id=track_id,
                category="samples"
            ))
        
        return cards
