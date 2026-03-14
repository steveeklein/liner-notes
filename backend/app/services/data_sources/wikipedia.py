from typing import List, Optional
import uuid
import os
import json
import httpx
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
        self.groq_api_key = os.getenv("GROQ_API_KEY")
    
    def _is_disambiguation(self, text: str) -> bool:
        """Check if a page is a disambiguation page."""
        lower = text.lower()[:1000]
        indicators = [
            "may refer to",
            "can refer to", 
            "refers to multiple",
            "disambiguation",
            "may also refer to",
            "commonly refers to"
        ]
        return any(ind in lower for ind in indicators)
    
    async def _resolve_disambiguation(self, page_text: str, artist: str, album: str, track: str) -> Optional[str]:
        """Use LLM to pick the correct Wikipedia page from disambiguation options."""
        if not self.groq_api_key:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.groq_api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": "llama-3.1-8b-instant",
                        "messages": [
                            {
                                "role": "system",
                                "content": """You help resolve Wikipedia disambiguation. Given disambiguation text and context about a song/artist/album, return the exact Wikipedia page title that best matches.

Return JSON: {"page_title": "Exact Page Title Here"} or {"page_title": null} if no match."""
                            },
                            {
                                "role": "user",
                                "content": f"""Context: Looking for info about the song "{track}" by {artist} from album "{album}".

Disambiguation text:
{page_text[:1500]}

Which Wikipedia page title matches this context best?"""
                            }
                        ],
                        "response_format": {"type": "json_object"},
                        "max_tokens": 100,
                        "temperature": 0.1
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    if content:
                        parsed = json.loads(content)
                        return parsed.get("page_title")
        except Exception as e:
            print(f"[Wikipedia] Disambiguation resolution error: {e}", flush=True)
        
        return None
    
    def _page_looks_like_music(self, page_text: str) -> bool:
        """Heuristic: page is about a band/artist if it mentions music-related terms early."""
        if not page_text or len(page_text) < 100:
            return False
        lower = page_text[:2000].lower()
        music_terms = ("band", "album", "music", "song", "singer", "guitar", "drummer", "bass", "recorded", "released", "musician", "rock", "pop", "genre")
        return any(term in lower for term in music_terms)

    def _page_looks_like_non_music_topic(self, page_text: str) -> bool:
        """Reject pages that are clearly about something other than a band/artist (e.g. Sugar the food)."""
        if not page_text or len(page_text) < 50:
            return False
        lower = page_text[:1500].lower()
        non_music_indicators = (
            "edible substances", "class of edible", "sweetener", "carbohydrate",
            "crystalline sugar", "table sugar", "sucrose", "fructose",
            "caloric sweetener", "sugar (food)", "culinary"
        )
        return any(ind in lower for ind in non_music_indicators)

    async def _get_page_with_disambiguation(self, search_terms: List[str], artist: str, album: str, track: str, content_check: str = None) -> Optional[tuple]:
        """Try search terms, handling disambiguation pages."""
        for search_term in search_terms:
            page = self.wiki.page(search_term)
            if not page.exists():
                continue

            # Check if it's a disambiguation page
            if self._is_disambiguation(page.text or ""):
                print(f"[Wikipedia] Found disambiguation for '{search_term}', resolving...", flush=True)
                resolved_title = await self._resolve_disambiguation(page.text or "", artist, album, track)
                if resolved_title:
                    resolved_page = self.wiki.page(resolved_title)
                    if resolved_page.exists() and not self._page_looks_like_non_music_topic(resolved_page.text or ""):
                        print(f"[Wikipedia] Resolved to: {resolved_title}", flush=True)
                        return (resolved_page, resolved_title)
                continue

            # For bare artist name (no "band"/"musician" in term), require page to look like music to avoid e.g. "Sugar" → sugar (food)
            if search_term == artist and not self._page_looks_like_music(page.text or ""):
                print(f"[Wikipedia] Skipping '{search_term}' — page doesn't look like music/artist", flush=True)
                continue

            # Reject pages that are clearly about a non-music topic (food, compound, etc.)
            if self._page_looks_like_non_music_topic(page.text or ""):
                print(f"[Wikipedia] Skipping '{search_term}' — page looks like non-music topic (e.g. food/compound)", flush=True)
                continue

            # Check content requirements if specified
            if content_check and content_check not in (page.text or "").lower()[:500]:
                continue

            return (page, search_term)

        return None
    
    def _format_summary(self, text: str, max_length: int = 500) -> str:
        """Format summary text to be more readable with front-loaded info."""
        if not text:
            return ""
        
        sentences = text.replace('\n', ' ').split('. ')
        
        formatted = []
        current_length = 0
        
        for sentence in sentences:
            sentence = sentence.strip()
            if not sentence:
                continue
            if not sentence.endswith('.'):
                sentence += '.'
            
            if current_length + len(sentence) > max_length:
                break
            
            formatted.append(sentence)
            current_length += len(sentence) + 1
        
        result = ' '.join(formatted)
        if len(text) > len(result):
            result = result.rstrip('.') + '...'
        
        return result
    
    def _format_full_content(self, text: str) -> str:
        """Format full content with proper paragraph breaks for detailed reading."""
        if not text:
            return ""
        
        # Split by various paragraph indicators
        paragraphs = text.replace('\n\n\n', '\n\n').split('\n\n')
        formatted_paragraphs = []
        total_length = 0
        max_length = 3000  # Allow more content for expanded view
        
        for para in paragraphs:
            para = para.strip()
            # Skip very short paragraphs, headers, or reference sections
            if len(para) < 50:
                continue
            if para.lower().startswith(('see also', 'references', 'external links', 'notes', 'bibliography')):
                break
            
            formatted_paragraphs.append(para)
            total_length += len(para)
            
            # Stop if we have enough content
            if total_length > max_length or len(formatted_paragraphs) >= 8:
                break
        
        return '\n\n'.join(formatted_paragraphs)
    
    async def fetch(
        self,
        artist: str,
        track_title: str,
        album: str,
        track_id: str
    ) -> List[InfoCard]:
        cards = []
        
        # Artist page — try (band) and (musician) first so we don't match "Sugar" → sugar (food), "Kiss" → kiss (act), etc.
        artist_result = await self._get_page_with_disambiguation(
            [f"{artist} (band)", f"{artist} (musician)", f"{artist} (singer)", artist],
            artist, album, track_title
        )
        if artist_result:
            artist_page, _ = artist_result
            summary = self._format_summary(artist_page.summary, max_length=400)
            full_content = self._format_full_content(artist_page.text[:8000]) if artist_page.text else None
            
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.WIKIPEDIA,
                title=f"About {artist}",
                summary=summary,
                full_content=full_content,
                url=artist_page.fullurl,
                track_id=track_id,
                category="artist"
            ))
        
        # Album page
        if album:
            album_searches = [
                f"{album} ({artist} album)",
                f"{album} (album)",
                album
            ]
            
            album_result = await self._get_page_with_disambiguation(
                album_searches, artist, album, track_title, content_check="album"
            )
            if album_result:
                album_page, _ = album_result
                summary = self._format_summary(album_page.summary, max_length=400)
                full_content = self._format_full_content(album_page.text[:8000]) if album_page.text else None
                
                cards.append(InfoCard(
                    id=str(uuid.uuid4()),
                    source=CardSource.WIKIPEDIA,
                    title=f"About '{album}'",
                    summary=summary,
                    full_content=full_content,
                    url=album_page.fullurl,
                    track_id=track_id,
                    category="album"
                ))
        
        # Song page
        song_searches = [
            f"{track_title} ({artist} song)",
            f"{track_title} (song)",
            track_title
        ]
        
        song_result = await self._get_page_with_disambiguation(
            song_searches, artist, album, track_title, content_check="song"
        )
        if song_result:
            song_page, _ = song_result
            summary = self._format_summary(song_page.summary, max_length=400)
            full_content = self._format_full_content(song_page.text[:8000]) if song_page.text else None
            
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.WIKIPEDIA,
                title=f"About '{track_title}'",
                summary=summary,
                full_content=full_content,
                url=song_page.fullurl,
                track_id=track_id,
                category="song"
            ))
        
        return cards
