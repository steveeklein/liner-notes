from typing import List
import uuid
import os
import json
import httpx

from app.models import InfoCard, CardSource
from .base import DataSource


class LLMSource(DataSource):
    """Generates contextual information using Groq (free tier with Llama 3.1)."""
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.1-8b-instant"
    
    async def fetch(
        self,
        artist: str,
        track_title: str,
        album: str,
        track_id: str,
        **kwargs
    ) -> List[InfoCard]:
        if not self.api_key:
            print("[LLM] No GROQ_API_KEY set, skipping", flush=True)
            return []
        variation = kwargs.get("variation", False)
        print(f"[LLM] Calling Groq API for: {track_title} by {artist}" + (" (variation)" if variation else ""), flush=True)

        cards = []

        if variation:
            system_content = """You are a music expert. The user is asking for FRESH insights they have not seen before. Return JSON with exactly 3 insights:
{
  "artist_insight": {"title": "3-5 words", "content": "1-2 paragraphs with DIFFERENT facts than a standard bio: lesser-known stories, specific anecdotes, a different angle, or deeper cut."},
  "album_insight": {"title": "3-5 words", "content": "1-2 paragraphs with DIFFERENT facts about this album - not the same summary. New angle, session details, or context."},
  "track_insight": {"title": "3-5 words", "content": "1-2 paragraphs with DIFFERENT facts about this song - behind-the-scenes, alternate take, or lesser-known detail."}
}
Rules: Be SPECIFIC. Do NOT repeat common biographical or summary content. Give NEW angles, lesser-known facts, or different aspects."""
        else:
            system_content = """You are a music expert. Return JSON with exactly 3 insights:
{
  "artist_insight": {"title": "3-5 words about artist", "content": "1-2 paragraphs with specific facts about the artist"},
  "album_insight": {"title": "3-5 words about album", "content": "1-2 paragraphs with specific facts about this album"},
  "track_insight": {"title": "3-5 words about track", "content": "1-2 paragraphs with specific facts about this specific song"}
}
Rules:
- Be SPECIFIC: mention dates, chart positions, collaborators, behind-the-scenes stories
- Lead each insight with the most surprising/interesting fact
- Keep each insight focused on its category (artist/album/track)
- If album is unknown, make album_insight about the artist's discography instead"""

        user_content = "Give me FRESH, different insights (not the same summary). " if variation else ""
        user_content += f"Insights about the song '{track_title}' by {artist}" + (f" from the album '{album}'" if album else "")

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": system_content},
                            {"role": "user", "content": user_content}
                        ],
                        "response_format": {"type": "json_object"},
                        "max_tokens": 800,
                        "temperature": 0.8 if variation else 0.7
                    },
                    timeout=15.0
                )
                
                print(f"[LLM] Groq response status: {response.status_code}", flush=True)
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    print(f"[LLM] Got content: {content[:200] if content else 'None'}...", flush=True)
                    
                    if content:
                        parsed = json.loads(content)
                        
                        # Artist insight
                        if parsed.get("artist_insight"):
                            ai = parsed["artist_insight"]
                            cards.append(InfoCard(
                                id=str(uuid.uuid4()),
                                source=CardSource.LLM,
                                title=ai.get("title", f"About {artist}"),
                                summary=ai.get("content", ""),
                                track_id=track_id,
                                category="artist"
                            ))
                        
                        # Album insight
                        if parsed.get("album_insight"):
                            ai = parsed["album_insight"]
                            cards.append(InfoCard(
                                id=str(uuid.uuid4()),
                                source=CardSource.LLM,
                                title=ai.get("title", f"About {album}"),
                                summary=ai.get("content", ""),
                                track_id=track_id,
                                category="album"
                            ))
                        
                        # Track insight
                        if parsed.get("track_insight"):
                            ti = parsed["track_insight"]
                            cards.append(InfoCard(
                                id=str(uuid.uuid4()),
                                source=CardSource.LLM,
                                title=ti.get("title", f"About {track_title}"),
                                summary=ti.get("content", ""),
                                track_id=track_id,
                                category="song"
                            ))
                        
                        print(f"[LLM] Created {len(cards)} cards", flush=True)
                else:
                    print(f"[LLM] Groq API error: {response.status_code} - {response.text}", flush=True)
        
        except Exception as e:
            print(f"LLM error: {e}", flush=True)
        
        return cards
