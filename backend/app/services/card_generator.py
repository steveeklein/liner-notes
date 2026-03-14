from typing import Optional, List, AsyncGenerator, Dict
import asyncio
import uuid
import os
from dotenv import load_dotenv

from app.models import InfoCard, CardSource, Track
from app.services.content_enhancer import content_enhancer
from app.services.data_sources import (
    WikipediaSource,
    AllMusicSource,
    WebSearchSource,
    LLMSource,
    GeniusSource,
    LastFmSource,
    MusicBrainzSource,
    DiscogsSource,
    WhoSampledSource,
    SetlistFmSource,
    YouTubeSource,
    RedditSource,
    SpotifyDataSource,
    BillboardSource,
)

load_dotenv()


class CardGenerator:
    """
    Generates info cards from multiple sources for a given track.
    Cards are generated asynchronously and streamed to the client.
    """
    
    def __init__(self):
        self.sources = {
            # High-priority sources (usually fast and reliable)
            CardSource.WIKIPEDIA: WikipediaSource(),
            CardSource.MUSICBRAINZ: MusicBrainzSource(),
            CardSource.GENIUS: GeniusSource(),
            
            # Music databases
            CardSource.ALLMUSIC: AllMusicSource(),
            CardSource.LASTFM: LastFmSource(),
            CardSource.DISCOGS: DiscogsSource(),
            
            # Samples & covers
            CardSource.WHOSAMPLED: WhoSampledSource(),
            
            # Charts & popularity
            CardSource.BILLBOARD: BillboardSource(),
            CardSource.SPOTIFY_DATA: SpotifyDataSource(),
            
            # Live performances
            CardSource.SETLISTFM: SetlistFmSource(),
            
            # Video content
            CardSource.YOUTUBE: YouTubeSource(),
            
            # Community discussions
            CardSource.REDDIT: RedditSource(),

            # General web search
            CardSource.WEB_SEARCH: WebSearchSource(),
            
            # AI-generated insights (run last as fallback/supplement)
            CardSource.LLM: LLMSource(),
        }
        self.cache: Dict[str, List[InfoCard]] = {}
        self.track_info: Dict[str, dict] = {}
    
    def set_track_info(self, track_id: str, artist: str, title: str, album: str):
        """Store track info for card generation."""
        self.track_info[track_id] = {
            "artist": artist,
            "title": title,
            "album": album
        }
    
    def _is_useful_card(self, card: InfoCard) -> bool:
        """
        Check if a card has useful content vs placeholder text.
        Returns False for cards that just say "go to X to see more".
        Album/credits cards (personnel, release info, genre) are kept even if short.
        """
        summary_lower = card.summary.lower()

        # Always keep AI (LLM) insights — user expects them every time
        if card.source == CardSource.LLM:
            return True

        # Keep album-related cards (personnel, release info, genre) — they're often short but useful
        if card.category in ("credits", "genre"):
            # Only reject if it's clearly garbage
            always_reject = [
                "no description available", "description not available",
                "information not found", "no data available", "coming soon",
            ]
            if any(p in summary_lower for p in always_reject):
                return False
            return True

        # Patterns that indicate placeholder/promotional content
        placeholder_patterns = [
            "explore", "view on", "check out", "discover more",
            "full discography on", "see more on", "find more at",
            "learn more about", "visit", "click to see",
            "browse the full", "for more information"
        ]

        # Patterns that are always rejected regardless of length
        always_reject_patterns = [
            "have the inside scoop",
            "sign up and drop some knowledge",
            "start the song bio",
            "song bio is",  # e.g. "This song bio is unreviewed"
            "unreviewed",
            "be the first to add",
            "add your own",
            "contribute to this page",
            "help us build",
            "no description available",
            "description not available",
            "information not found",
            "we don't have",
            "we couldn't find",
            "no information found",
            "no data available",
            "coming soon",
        ]

        # Check always-reject patterns first
        for pattern in always_reject_patterns:
            if pattern in summary_lower:
                print(f"[Cards] Filtering out placeholder card (always reject): {card.title}", flush=True)
                return False

        # Check conditional patterns (only reject if short)
        for pattern in placeholder_patterns:
            if pattern in summary_lower and len(card.summary) < 100:
                print(f"[Cards] Filtering out placeholder card: {card.title}", flush=True)
                return False

        # Reject very short content (except album/credits, handled above)
        if len(card.summary.strip()) < 30:
            print(f"[Cards] Filtering out short card: {card.title}", flush=True)
            return False

        return True
    
    def _assign_default_section(self, card: InfoCard) -> str:
        """Assign a default section based on source and category."""
        if card.category == "artist":
            return "artist"
        if card.category == "album":
            return "album"
        if card.category == "credits" and ("personnel" in card.title.lower() or "playing on" in card.title.lower()):
            return "album"
        if card.category in ["reviews", "trivia", "similar", "concerts", "videos"]:
            return "discussions"
        if card.source == CardSource.REDDIT:
            return "discussions"
        return "song"

    async def _fetch_from_source(
        self, source_type: CardSource, track_id: str
    ) -> List[InfoCard]:
        """Fetch cards from a single source. Used by generate_cards_stream and refresh_section."""
        if track_id not in self.track_info:
            return []
        info = self.track_info[track_id]
        artist = info["artist"]
        title = info["title"]
        album = info["album"]
        SOURCE_TIMEOUT = 25.0
        ENHANCE_CARD_TIMEOUT = 20.0

        source = self.sources[source_type]
        try:
            print(f"[Cards] Fetching from {source_type.value}...", flush=True)
            cards = await asyncio.wait_for(
                source.fetch(
                    artist=artist,
                    track_title=title,
                    album=album,
                    track_id=track_id,
                ),
                timeout=SOURCE_TIMEOUT,
            )
            print(f"[Cards] {source_type.value} returned {len(cards)} cards", flush=True)

            if cards:
                cards = [c for c in cards if self._is_useful_card(c)]

                if cards and source_type != CardSource.LLM:
                    to_enhance = []
                    for i, card in enumerate(cards):
                        if card.category == "credits":
                            cards[i].section = self._assign_default_section(card)
                        elif len(card.summary) >= 150:
                            to_enhance.append((i, card))
                        else:
                            cards[i].section = self._assign_default_section(card)
                    if to_enhance:
                        async def enhance_one(idx: int, c: InfoCard) -> tuple[int, InfoCard]:
                            try:
                                enhanced = await asyncio.wait_for(
                                    content_enhancer.enhance_card(c),
                                    timeout=ENHANCE_CARD_TIMEOUT,
                                )
                                return (idx, enhanced)
                            except (asyncio.TimeoutError, Exception) as e:
                                kind = "timeout" if isinstance(e, asyncio.TimeoutError) else "error"
                                print(f"[Cards] Enhancement {kind} for card: {e}", flush=True)
                                c.section = self._assign_default_section(c)
                                return (idx, c)

                        results = await asyncio.gather(
                            *[enhance_one(i, c) for i, c in to_enhance],
                            return_exceptions=False,
                        )
                        for idx, enhanced_card in results:
                            cards[idx] = enhanced_card
                        print(f"[Cards] Enhanced {len(to_enhance)} cards from {source_type.value}", flush=True)
                else:
                    for i, card in enumerate(cards):
                        cards[i].section = self._assign_default_section(card)

            return cards
        except asyncio.TimeoutError:
            print(f"[Cards] Timeout from {source_type.value} ({SOURCE_TIMEOUT}s)", flush=True)
            return []
        except Exception as e:
            print(f"[Cards] Error from {source_type.value}: {e}", flush=True)
            return []

    async def generate_cards_stream(self, track_id: str) -> AsyncGenerator[InfoCard, None]:
        """
        Stream cards as they're generated from various sources.
        Each source generates cards asynchronously, allowing cards
        to appear progressively in the UI.
        """
        print(f"[Cards] Generating cards for track_id: {track_id}", flush=True)
        print(f"[Cards] Known tracks: {list(self.track_info.keys())}", flush=True)
        
        if track_id not in self.track_info:
            print(f"[Cards] ERROR: No track info for {track_id}. Need to fetch playback state first.", flush=True)
            return
        
        # Priority sources: Run early so we always have content. LLM gives AI insights every time (when GROQ key set).
        priority_sources = [
            CardSource.LLM,  # AI insights — always run first so there are always AI cards
            CardSource.WIKIPEDIA,
            CardSource.GENIUS,  # Has free fallback
            CardSource.MUSICBRAINZ,
            CardSource.DISCOGS,  # Free public API
        ]
        
        # Secondary sources: Mix of free and paid
        secondary_sources = [
            CardSource.REDDIT,  # Free public API
            CardSource.WEB_SEARCH,  # DuckDuckGo fallback is free
            CardSource.SPOTIFY_DATA,  # Uses existing auth
            CardSource.LASTFM,  # Requires API key
            CardSource.ALLMUSIC,  # Web scraping (may be flaky)
        ]
        
        # Tertiary sources: Web scraping or paid APIs
        tertiary_sources = [
            CardSource.WHOSAMPLED,  # Web scraping
            CardSource.BILLBOARD,  # Web scraping
            CardSource.SETLISTFM,  # Requires API key
            CardSource.YOUTUBE,  # Requires API key
        ]
        
        cached_cards = []
        
        priority_tasks = [
            asyncio.create_task(self._fetch_from_source(source_type, track_id))
            for source_type in priority_sources
            if source_type in self.sources
        ]
        
        for task in asyncio.as_completed(priority_tasks):
            try:
                cards = await task
                for card in cards:
                    cached_cards.append(card)
                    yield card
            except Exception as e:
                print(f"Error in priority card generation: {e}")
        
        secondary_tasks = [
            asyncio.create_task(self._fetch_from_source(source_type, track_id))
            for source_type in secondary_sources
            if source_type in self.sources
        ]
        
        for task in asyncio.as_completed(secondary_tasks):
            try:
                cards = await task
                for card in cards:
                    cached_cards.append(card)
                    yield card
            except Exception as e:
                print(f"Error in secondary card generation: {e}")
        
        tertiary_tasks = [
            asyncio.create_task(self._fetch_from_source(source_type, track_id))
            for source_type in tertiary_sources
            if source_type in self.sources
        ]
        
        for task in asyncio.as_completed(tertiary_tasks):
            try:
                cards = await task
                for card in cards:
                    cached_cards.append(card)
                    yield card
            except Exception as e:
                print(f"Error in tertiary card generation: {e}")
        
        self.cache[track_id] = sorted(
            cached_cards,
            key=lambda c: c.relevance_score,
            reverse=True
        )
        info = self.track_info[track_id]
        print(f"[Cards] Done: {len(cached_cards)} cards for {info['artist']} - {info['title']}", flush=True)
    
    async def get_cards(
        self, 
        track_id: str, 
        source: Optional[str] = None
    ) -> List[InfoCard]:
        """Get all cards for a track, optionally filtered by source."""
        if track_id in self.cache:
            cards = self.cache[track_id]
            if source:
                cards = [c for c in cards if c.source.value == source]
            return cards
        
        cards = []
        async for card in self.generate_cards_stream(track_id):
            cards.append(card)
        
        if source:
            cards = [c for c in cards if c.source.value == source]
        
        return cards
    
    async def get_card_detail(self, track_id: str, card_id: str) -> Optional[InfoCard]:
        """Get a specific card with full content."""
        if track_id in self.cache:
            for card in self.cache[track_id]:
                if card.id == card_id:
                    return card
        return None
    
    async def invalidate_cache(self, track_id: str):
        """Clear cached cards for a track."""
        if track_id in self.cache:
            del self.cache[track_id]
    
    def get_available_sources(self) -> List[str]:
        """Return list of all available data sources."""
        return [source.value for source in self.sources.keys()]


card_generator = CardGenerator()
