from typing import List
import uuid
import os
import httpx

from app.models import InfoCard, CardSource
from .base import DataSource


class WebSearchSource(DataSource):
    """Fetches information via web search (SerpAPI or DuckDuckGo)."""
    
    def __init__(self):
        self.serpapi_key = os.getenv("SERPAPI_KEY")
    
    async def _search_serpapi(self, query: str) -> List[dict]:
        """Search using SerpAPI (Google)."""
        if not self.serpapi_key:
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://serpapi.com/search",
                    params={
                        "q": query,
                        "api_key": self.serpapi_key,
                        "num": 5
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = []
                    
                    for item in data.get("organic_results", [])[:5]:
                        results.append({
                            "title": item.get("title", ""),
                            "snippet": item.get("snippet", ""),
                            "url": item.get("link", "")
                        })
                    
                    return results
        except Exception as e:
            print(f"SerpAPI error: {e}")
        
        return []
    
    async def _search_duckduckgo(self, query: str) -> List[dict]:
        """Fallback search using DuckDuckGo HTML."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://html.duckduckgo.com/html/",
                    params={"q": query},
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(response.text, 'html.parser')
                    
                    results = []
                    for result in soup.select('.result')[:5]:
                        title_elem = result.select_one('.result__title')
                        snippet_elem = result.select_one('.result__snippet')
                        link_elem = result.select_one('.result__url')
                        
                        if title_elem:
                            results.append({
                                "title": title_elem.get_text(strip=True),
                                "snippet": snippet_elem.get_text(strip=True) if snippet_elem else "",
                                "url": link_elem.get('href', '') if link_elem else ""
                            })
                    
                    return results
        except Exception as e:
            print(f"DuckDuckGo error: {e}")
        
        return []
    
    async def fetch(
        self,
        artist: str,
        track_title: str,
        album: str,
        track_id: str
    ) -> List[InfoCard]:
        cards = []
        
        queries = [
            f'"{artist}" "{track_title}" story behind song',
            f'"{artist}" interesting facts trivia',
        ]
        
        for query in queries:
            if self.serpapi_key:
                results = await self._search_serpapi(query)
            else:
                results = await self._search_duckduckgo(query)
            
            for result in results[:2]:
                if result["snippet"]:
                    cards.append(InfoCard(
                        id=str(uuid.uuid4()),
                        source=CardSource.WEB_SEARCH,
                        title=result["title"][:100],
                        summary=result["snippet"],
                        url=result["url"],
                        track_id=track_id,
                        category="trivia"
                    ))
        
        return cards
