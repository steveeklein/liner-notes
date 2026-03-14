from typing import List
import uuid
import httpx
from bs4 import BeautifulSoup

from app.models import InfoCard, CardSource
from .base import DataSource


class BillboardSource(DataSource):
    """Fetches chart history and rankings from Billboard."""
    
    BASE_URL = "https://www.billboard.com"
    
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
    
    async def _search_charts(self, artist: str, title: str) -> dict | None:
        """Search for chart history."""
        try:
            search_query = f"{artist} {title}".replace(" ", "+")
            url = f"{self.BASE_URL}/search/{search_query}"
            
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers, timeout=15.0)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    results = soup.select('.search-result-item, .a-search-grid__item')
                    for result in results:
                        title_elem = result.select_one('.title, h3')
                        if title_elem:
                            result_title = title_elem.get_text(strip=True).lower()
                            if artist.lower() in result_title or title.lower() in result_title:
                                link = result.select_one('a')
                                if link:
                                    return {
                                        "title": title_elem.get_text(strip=True),
                                        "url": self.BASE_URL + link.get('href', '')
                                    }
        except Exception as e:
            print(f"Billboard search error: {e}")
        return None
    
    async def _get_artist_chart_history(self, artist: str) -> List[dict]:
        """Get artist's chart history."""
        try:
            artist_slug = artist.lower().replace(" ", "-").replace("'", "")
            url = f"{self.BASE_URL}/artist/{artist_slug}/chart-history/hsi"
            
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers, timeout=15.0)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    chart_entries = []
                    entries = soup.select('.chart-history-entry, .artist-chart-row')
                    
                    for entry in entries[:10]:
                        song_elem = entry.select_one('.chart-history-entry__title, .c-title')
                        peak_elem = entry.select_one('.chart-history-entry__peak, .c-flex')
                        
                        if song_elem:
                            chart_entries.append({
                                "song": song_elem.get_text(strip=True),
                                "peak": peak_elem.get_text(strip=True) if peak_elem else None
                            })
                    
                    return chart_entries
        except Exception as e:
            print(f"Billboard chart history error: {e}")
        return []
    
    async def _check_current_charts(self, artist: str, title: str) -> dict | None:
        """Check if song is on current Hot 100."""
        try:
            url = f"{self.BASE_URL}/charts/hot-100"
            
            async with httpx.AsyncClient(follow_redirects=True) as client:
                response = await client.get(url, headers=self.headers, timeout=15.0)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    entries = soup.select('.o-chart-results-list-row')
                    for i, entry in enumerate(entries, 1):
                        song_elem = entry.select_one('.c-title')
                        artist_elem = entry.select_one('.c-label')
                        
                        if song_elem and artist_elem:
                            chart_song = song_elem.get_text(strip=True).lower()
                            chart_artist = artist_elem.get_text(strip=True).lower()
                            
                            if (title.lower() in chart_song and 
                                artist.lower() in chart_artist):
                                return {
                                    "position": i,
                                    "song": song_elem.get_text(strip=True),
                                    "artist": artist_elem.get_text(strip=True)
                                }
        except Exception as e:
            print(f"Billboard current charts error: {e}")
        return None
    
    async def fetch(
        self,
        artist: str,
        track_title: str,
        album: str,
        track_id: str,
        **kwargs
    ) -> List[InfoCard]:
        cards = []
        
        current = await self._check_current_charts(artist, track_title)
        if current:
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.BILLBOARD,
                title="Currently Charting!",
                summary=f"#{current['position']} on the Billboard Hot 100",
                url=f"{self.BASE_URL}/charts/hot-100",
                track_id=track_id,
                category="charts",
                relevance_score=1.5
            ))
        
        chart_history = await self._get_artist_chart_history(artist)
        if chart_history:
            track_lower = track_title.lower()
            for entry in chart_history:
                if track_lower in entry["song"].lower():
                    peak = entry.get("peak", "")
                    cards.append(InfoCard(
                        id=str(uuid.uuid4()),
                        source=CardSource.BILLBOARD,
                        title="Chart History",
                        summary=f"'{track_title}' peaked at #{peak} on the Billboard charts" if peak else f"'{track_title}' charted on Billboard",
                        url=f"{self.BASE_URL}/artist/{artist.lower().replace(' ', '-')}/chart-history",
                        track_id=track_id,
                        category="charts"
                    ))
                    break
            
            if chart_history and not any(c.title == "Chart History" for c in cards):
                top_songs = [e["song"] for e in chart_history[:5]]
                cards.append(InfoCard(
                    id=str(uuid.uuid4()),
                    source=CardSource.BILLBOARD,
                    title=f"{artist}'s Billboard Hits",
                    summary=f"Chart hits include: {', '.join(top_songs)}",
                    url=f"{self.BASE_URL}/artist/{artist.lower().replace(' ', '-')}/chart-history",
                    track_id=track_id,
                    category="charts"
                ))
        
        return cards
