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
        """
        if not self.api_key:
            return card
        
        if len(card.summary) < 100:
            return card
        
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
                            {
                                "role": "system",
                                "content": """Reformat music info for readability. Return JSON:
{"summary": "max 400 chars, most interesting facts first", "full_content": "enhanced full version or null"}

Rules: Front-load interesting facts. Short paragraphs. Remove filler phrases. Keep facts accurate."""
                            },
                            {
                                "role": "user",
                                "content": f"Enhance:\n\nSummary: {card.summary[:500]}\n\nFull: {(card.full_content or 'None')[:500]}"
                            }
                        ],
                        "response_format": {"type": "json_object"},
                        "max_tokens": 500,
                        "temperature": 0.3
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    content = data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    
                    if content:
                        parsed = json.loads(content)
                        enhanced_summary = parsed.get("summary", card.summary)
                        enhanced_full = parsed.get("full_content")
                        
                        if enhanced_summary:
                            card.summary = enhanced_summary
                        if enhanced_full and card.full_content:
                            card.full_content = enhanced_full
        
        except Exception as e:
            print(f"Content enhancement error: {e}", flush=True)
        
        return card
    
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
