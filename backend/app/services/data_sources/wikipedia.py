from typing import List
import uuid
import wikipediaapi

from app.models import InfoCard, CardSource
from .base import DataSource


class WikipediaSource(DataSource):
    """Fetches information from Wikipedia."""
    
    def __init__(self):
        self.wiki = wikipediaapi.Wikipedia(
            user_agent='LinerNotes/1.0 (contact@example.com)',
            language='en'
        )
    
    async def fetch(
        self,
        artist: str,
        track_title: str,
        album: str,
        track_id: str
    ) -> List[InfoCard]:
        cards = []
        
        artist_page = self.wiki.page(artist)
        if artist_page.exists():
            summary = artist_page.summary[:500]
            if len(artist_page.summary) > 500:
                summary += "..."
            
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.WIKIPEDIA,
                title=f"About {artist}",
                summary=summary,
                full_content=artist_page.text[:3000] if artist_page.text else None,
                url=artist_page.fullurl,
                track_id=track_id,
                category="artist"
            ))
        
        if album:
            album_searches = [
                f"{album} (album)",
                f"{album} ({artist} album)",
                album
            ]
            
            for search_term in album_searches:
                album_page = self.wiki.page(search_term)
                if album_page.exists() and "album" in album_page.text.lower()[:500]:
                    summary = album_page.summary[:500]
                    if len(album_page.summary) > 500:
                        summary += "..."
                    
                    cards.append(InfoCard(
                        id=str(uuid.uuid4()),
                        source=CardSource.WIKIPEDIA,
                        title=f"About '{album}'",
                        summary=summary,
                        full_content=album_page.text[:3000] if album_page.text else None,
                        url=album_page.fullurl,
                        track_id=track_id,
                        category="album"
                    ))
                    break
        
        song_searches = [
            f"{track_title} ({artist} song)",
            f"{track_title} (song)",
            track_title
        ]
        
        for search_term in song_searches:
            song_page = self.wiki.page(search_term)
            if song_page.exists() and "song" in song_page.text.lower()[:500]:
                summary = song_page.summary[:500]
                if len(song_page.summary) > 500:
                    summary += "..."
                
                cards.append(InfoCard(
                    id=str(uuid.uuid4()),
                    source=CardSource.WIKIPEDIA,
                    title=f"About '{track_title}'",
                    summary=summary,
                    full_content=song_page.text[:3000] if song_page.text else None,
                    url=song_page.fullurl,
                    track_id=track_id,
                    category="song"
                ))
                break
        
        return cards
