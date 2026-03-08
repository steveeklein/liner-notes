from typing import List
import uuid
import httpx
from bs4 import BeautifulSoup
import asyncio

from app.models import InfoCard, CardSource
from .base import DataSource


class AllMusicSource(DataSource):
    """Fetches information from AllMusic via web scraping."""
    
    BASE_URL = "https://www.allmusic.com"
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
    
    async def _search_artist(self, artist: str) -> dict | None:
        """Search for an artist on AllMusic."""
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    f"{self.BASE_URL}/search/artists/{artist.replace(' ', '+')}",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    result = soup.select_one('.search-results .artist')
                    if result:
                        link = result.select_one('a')
                        if link:
                            return {
                                "name": link.get_text(strip=True),
                                "url": self.BASE_URL + link.get('href', '')
                            }
        except Exception as e:
            print(f"AllMusic search error: {e}")
        
        return None
    
    async def _get_artist_bio(self, artist_url: str) -> dict | None:
        """Get artist biography from AllMusic."""
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    f"{artist_url}/biography",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    bio_elem = soup.select_one('.biography-text, .text')
                    if bio_elem:
                        bio_text = bio_elem.get_text(strip=True)
                        return {
                            "bio": bio_text,
                            "url": artist_url
                        }
        except Exception as e:
            print(f"AllMusic bio error: {e}")
        
        return None
    
    async def _get_artist_info(self, artist_url: str) -> dict | None:
        """Get artist info (genres, styles, influences) from AllMusic."""
        try:
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(
                    artist_url,
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    info = {}
                    
                    genres_elem = soup.select('.genre a')
                    if genres_elem:
                        info["genres"] = [g.get_text(strip=True) for g in genres_elem[:5]]
                    
                    styles_elem = soup.select('.styles a')
                    if styles_elem:
                        info["styles"] = [s.get_text(strip=True) for s in styles_elem[:5]]
                    
                    return info if info else None
        except Exception as e:
            print(f"AllMusic info error: {e}")
        
        return None
    
    async def fetch(
        self,
        artist: str,
        track_title: str,
        album: str,
        track_id: str
    ) -> List[InfoCard]:
        cards = []
        
        artist_result = await self._search_artist(artist)
        if not artist_result:
            return cards
        
        bio_task = asyncio.create_task(self._get_artist_bio(artist_result["url"]))
        info_task = asyncio.create_task(self._get_artist_info(artist_result["url"]))
        
        bio_data, info_data = await asyncio.gather(bio_task, info_task)
        
        if bio_data:
            summary = bio_data["bio"][:400]
            if len(bio_data["bio"]) > 400:
                summary += "..."
            
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.ALLMUSIC,
                title=f"{artist} - Biography",
                summary=summary,
                full_content=bio_data["bio"],
                url=bio_data["url"],
                track_id=track_id,
                category="artist"
            ))
        
        if info_data:
            genre_text = ""
            if "genres" in info_data:
                genre_text += f"Genres: {', '.join(info_data['genres'])}"
            if "styles" in info_data:
                if genre_text:
                    genre_text += " | "
                genre_text += f"Styles: {', '.join(info_data['styles'])}"
            
            if genre_text:
                cards.append(InfoCard(
                    id=str(uuid.uuid4()),
                    source=CardSource.ALLMUSIC,
                    title=f"{artist} - Musical Style",
                    summary=genre_text,
                    url=artist_result["url"],
                    track_id=track_id,
                    category="genre"
                ))
        
        return cards
