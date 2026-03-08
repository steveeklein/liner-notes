from pydantic import BaseModel
from typing import Optional, List, Literal
from enum import Enum


class MusicProvider(str, Enum):
    SPOTIFY = "spotify"
    TIDAL = "tidal"
    QOBUZ = "qobuz"


class LoginRequest(BaseModel):
    provider: MusicProvider
    username: str
    password: str


class AuthStatus(BaseModel):
    authenticated: bool
    provider: Optional[MusicProvider] = None
    user_name: Optional[str] = None


class Track(BaseModel):
    id: str
    title: str
    artist: str
    album: str
    duration: int
    cover_url: Optional[str] = None
    provider: MusicProvider


class PlaybackState(BaseModel):
    is_playing: bool
    current_track: Optional[Track] = None
    position: int = 0


class CardSource(str, Enum):
    # Knowledge bases
    WIKIPEDIA = "wikipedia"
    MUSICBRAINZ = "musicbrainz"
    DISCOGS = "discogs"
    
    # Music databases & reviews
    ALLMUSIC = "allmusic"
    LASTFM = "lastfm"
    RATEYOURMUSIC = "rateyourmusic"
    ALBUMOFTHEYEAR = "albumoftheyear"
    PITCHFORK = "pitchfork"
    
    # Lyrics & analysis
    GENIUS = "genius"
    SONGMEANINGS = "songmeanings"
    
    # Samples & covers
    WHOSAMPLED = "whosampled"
    SECONDHANDSONGS = "secondhandsongs"
    
    # Live & concerts
    SETLISTFM = "setlistfm"
    SONGKICK = "songkick"
    BANDSINTOWN = "bandsintown"
    
    # Video & media
    YOUTUBE = "youtube"
    IMDB = "imdb"
    
    # Charts & stats
    BILLBOARD = "billboard"
    SPOTIFY_DATA = "spotify_data"
    
    # Social & community
    REDDIT = "reddit"
    
    # General web
    WEB_SEARCH = "web_search"
    
    # AI-generated
    LLM = "llm"


class InfoCard(BaseModel):
    id: str
    source: CardSource
    title: str
    summary: str
    full_content: Optional[str] = None
    url: Optional[str] = None
    image_url: Optional[str] = None
    track_id: str
    category: Literal[
        "artist", "album", "song", "genre", "trivia", 
        "lyrics", "samples", "credits", "reviews", 
        "charts", "concerts", "videos", "similar", "history"
    ]
    relevance_score: float = 1.0


class SearchResult(BaseModel):
    tracks: List[Track]
    albums: List[dict]
    artists: List[dict]
