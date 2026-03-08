from typing import Optional, List, AsyncGenerator, Dict
import asyncio
import uuid
import os
from dotenv import load_dotenv

from app.models import InfoCard, CardSource, Track
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
    
    async def generate_cards_stream(self, track_id: str) -> AsyncGenerator[InfoCard, None]:
        """
        Stream cards as they're generated from various sources.
        Each source generates cards asynchronously, allowing cards
        to appear progressively in the UI.
        """
        if track_id not in self.track_info:
            return
        
        info = self.track_info[track_id]
        artist = info["artist"]
        title = info["title"]
        album = info["album"]
        
        async def fetch_from_source(source_type: CardSource):
            source = self.sources[source_type]
            try:
                cards = await source.fetch(
                    artist=artist,
                    track_title=title,
                    album=album,
                    track_id=track_id
                )
                return cards
            except Exception as e:
                print(f"Error fetching from {source_type}: {e}")
                return []
        
        priority_sources = [
            CardSource.WIKIPEDIA,
            CardSource.GENIUS,
            CardSource.MUSICBRAINZ,
        ]
        
        secondary_sources = [
            CardSource.LASTFM,
            CardSource.ALLMUSIC,
            CardSource.DISCOGS,
            CardSource.WHOSAMPLED,
            CardSource.SPOTIFY_DATA,
        ]
        
        tertiary_sources = [
            CardSource.BILLBOARD,
            CardSource.SETLISTFM,
            CardSource.YOUTUBE,
            CardSource.REDDIT,
            CardSource.WEB_SEARCH,
            CardSource.LLM,
        ]
        
        cached_cards = []
        
        priority_tasks = [
            asyncio.create_task(fetch_from_source(source_type))
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
            asyncio.create_task(fetch_from_source(source_type))
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
            asyncio.create_task(fetch_from_source(source_type))
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
