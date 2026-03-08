from typing import List
import uuid
import os
import json
from openai import AsyncOpenAI

from app.models import InfoCard, CardSource
from .base import DataSource


class LLMSource(DataSource):
    """Generates contextual information using LLM."""
    
    def __init__(self):
        api_key = os.getenv("OPENAI_API_KEY")
        self.client = AsyncOpenAI(api_key=api_key) if api_key else None
    
    async def fetch(
        self,
        artist: str,
        track_title: str,
        album: str,
        track_id: str
    ) -> List[InfoCard]:
        if not self.client:
            return []
        
        cards = []
        
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": """You are a music expert providing interesting context about songs and artists.
                        Return JSON with the following structure:
                        {
                            "insights": [
                                {
                                    "title": "Brief title",
                                    "content": "2-3 sentence insight",
                                    "category": "artist|song|album|trivia"
                                }
                            ]
                        }
                        Provide 2-3 unique, interesting insights about the song, artist, or album."""
                    },
                    {
                        "role": "user",
                        "content": f"Provide interesting insights about '{track_title}' by {artist}"
                        + (f" from the album '{album}'" if album else "")
                    }
                ],
                response_format={"type": "json_object"},
                max_tokens=500,
                temperature=0.7
            )
            
            content = response.choices[0].message.content
            if content:
                data = json.loads(content)
                
                for insight in data.get("insights", []):
                    cards.append(InfoCard(
                        id=str(uuid.uuid4()),
                        source=CardSource.LLM,
                        title=insight.get("title", "Music Insight"),
                        summary=insight.get("content", ""),
                        track_id=track_id,
                        category=insight.get("category", "trivia")
                    ))
        
        except Exception as e:
            print(f"LLM error: {e}")
        
        return cards
