"""
Content enhancer using Groq (free tier) to clean up and format card content.
Makes information more readable with proper paragraphs and structure.
"""
import os
import json
import httpx

from app.models import InfoCard


class ContentEnhancer:
    """Enhances card content using Groq LLM for better readability."""
    
    def __init__(self):
        self.api_key = os.getenv("GROQ_API_KEY")
        self.base_url = "https://api.groq.com/openai/v1/chat/completions"
        self.model = "llama-3.1-8b-instant"
    
    async def enhance_card(self, card: InfoCard) -> InfoCard:
        """
        Enhance a card's content for better readability.
        - Formats text into readable paragraphs
        - Front-loads the most interesting information
        - Removes filler and redundant phrases
        - Assigns the card to the best section
        """
        if not self.api_key:
            card.section = self._default_section(card)
            return card
        
        if len(card.summary) < 100:
            card.section = self._default_section(card)
            return card
        
        try:
            # Combine all available content for the LLM
            original_content = card.full_content or card.summary
            
            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.post(
                    self.base_url,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    json={
                        "model": self.model,
                        "messages": [
                            {
                                "role": "system",
                                "content": """Reformat music info for readability. Return JSON:
{
  "summary": "2-3 sentences, max 350 chars. Most interesting/hook fact first.",
  "full_content": "Detailed, well-formatted content with multiple paragraphs. Use \\n\\n between paragraphs.",
  "section": "one of: artist, album, song, discussions"
}

FULL_CONTENT RULES:
- Write 3-5 substantial paragraphs (separated by \\n\\n)
- Include ALL interesting facts from the source
- Add context and background information
- Use engaging, readable prose
- Each paragraph should cover a distinct aspect
- Total length: 800-1500 characters

Section guide:
- artist: Biography, career, personal facts about musician/band
- album: Production, recording, context, significance
- song: Lyrics meaning, composition, samples, charts, background
- discussions: Reviews, opinions, trivia, live performances"""
                            },
                            {
                                "role": "user",
                                "content": f"Title: {card.title}\nSource: {card.source.value}\nCategory: {card.category}\n\nContent to enhance:\n{original_content[:2000]}"
                            }
                        ],
                        "response_format": {"type": "json_object"},
                        "max_tokens": 1000,
                        "temperature": 0.4
                    },
                    timeout=15.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    if content:
                        parsed = json.loads(content)
                        enhanced_summary = parsed.get("summary", card.summary)
                        enhanced_full = parsed.get("full_content")
                        section = parsed.get("section", "song")
                        
                        if enhanced_summary:
                            card.summary = enhanced_summary
                        # Always set full_content if we got a good enhanced version
                        if enhanced_full and len(enhanced_full) > len(card.summary):
                            card.full_content = enhanced_full
                        if section in ["artist", "album", "song", "discussions"]:
                            card.section = section
                        else:
                            card.section = self._default_section(card)
                else:
                    card.section = self._default_section(card)
        
        except Exception as e:
            print(f"Content enhancement error: {e}", flush=True)
            card.section = self._default_section(card)
        
        return card
    
    def _default_section(self, card: InfoCard) -> str:
        """Assign a default section based on source and category."""
        if card.category == "artist":
            return "artist"
        if card.category == "album":
            return "album"
        if card.category in ["reviews", "trivia", "similar", "concerts", "videos"]:
            return "discussions"
        if card.source.value == "reddit":
            return "discussions"
        return "song"
    
    async def enhance_batch(self, cards: list[InfoCard], max_cards: int = 5) -> list[InfoCard]:
        """
        Enhance multiple cards. Limits to max_cards to control API costs.
        Prioritizes cards with longer content that benefit most from enhancement.
        """
        if not self.client:
            return cards
        
        cards_to_enhance = sorted(
            [(i, c) for i, c in enumerate(cards) if len(c.summary) >= 150],
            key=lambda x: len(x[1].summary) + len(x[1].full_content or ""),
            reverse=True
        )[:max_cards]
        
        for idx, card in cards_to_enhance:
            cards[idx] = await self.enhance_card(card)
        
        return cards


content_enhancer = ContentEnhancer()
