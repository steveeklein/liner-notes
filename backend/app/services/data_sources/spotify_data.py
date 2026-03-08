from typing import List
import uuid
import os
import httpx
import base64

from app.models import InfoCard, CardSource
from .base import DataSource


class SpotifyDataSource(DataSource):
    """
    Fetches audio features and related artists from Spotify.
    Note: Used for metadata only, not playback.
    """
    
    BASE_URL = "https://api.spotify.com/v1"
    AUTH_URL = "https://accounts.spotify.com/api/token"
    
    def __init__(self):
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.access_token = None
    
    async def _get_access_token(self) -> str | None:
        """Get Spotify access token using client credentials."""
        if not self.client_id or not self.client_secret:
            return None
        
        if self.access_token:
            return self.access_token
        
        try:
            credentials = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.AUTH_URL,
                    data={"grant_type": "client_credentials"},
                    headers={"Authorization": f"Basic {credentials}"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data.get("access_token")
                    return self.access_token
        except Exception as e:
            print(f"Spotify auth error: {e}")
        return None
    
    async def _search_track(self, artist: str, title: str) -> dict | None:
        """Search for a track on Spotify."""
        token = await self._get_access_token()
        if not token:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/search",
                    params={
                        "q": f"artist:{artist} track:{title}",
                        "type": "track",
                        "limit": 1
                    },
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    tracks = data.get("tracks", {}).get("items", [])
                    if tracks:
                        return tracks[0]
        except Exception as e:
            print(f"Spotify search error: {e}")
        return None
    
    async def _get_audio_features(self, track_id: str) -> dict | None:
        """Get audio features for a track."""
        token = await self._get_access_token()
        if not token:
            return None
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/audio-features/{track_id}",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"Spotify audio features error: {e}")
        return None
    
    async def _get_related_artists(self, artist_id: str) -> List[dict]:
        """Get related artists."""
        token = await self._get_access_token()
        if not token:
            return []
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/artists/{artist_id}/related-artists",
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("artists", [])[:10]
        except Exception as e:
            print(f"Spotify related artists error: {e}")
        return []
    
    def _describe_audio_features(self, features: dict) -> str:
        """Generate human-readable description of audio features."""
        descriptions = []
        
        energy = features.get("energy", 0)
        if energy > 0.8:
            descriptions.append("high energy")
        elif energy < 0.3:
            descriptions.append("calm and mellow")
        
        valence = features.get("valence", 0)
        if valence > 0.7:
            descriptions.append("upbeat and positive")
        elif valence < 0.3:
            descriptions.append("melancholic")
        
        danceability = features.get("danceability", 0)
        if danceability > 0.7:
            descriptions.append("highly danceable")
        
        acousticness = features.get("acousticness", 0)
        if acousticness > 0.7:
            descriptions.append("acoustic-driven")
        
        instrumentalness = features.get("instrumentalness", 0)
        if instrumentalness > 0.5:
            descriptions.append("largely instrumental")
        
        tempo = features.get("tempo", 0)
        if tempo:
            descriptions.append(f"{int(tempo)} BPM")
        
        key_names = ["C", "C♯", "D", "D♯", "E", "F", "F♯", "G", "G♯", "A", "A♯", "B"]
        key = features.get("key", -1)
        mode = features.get("mode", 0)
        if key >= 0:
            mode_name = "major" if mode == 1 else "minor"
            descriptions.append(f"Key of {key_names[key]} {mode_name}")
        
        return ", ".join(descriptions) if descriptions else "Audio analysis available"
    
    async def fetch(
        self,
        artist: str,
        track_title: str,
        album: str,
        track_id: str
    ) -> List[InfoCard]:
        cards = []
        
        track = await self._search_track(artist, track_title)
        if not track:
            return cards
        
        spotify_track_id = track.get("id")
        if spotify_track_id:
            features = await self._get_audio_features(spotify_track_id)
            if features:
                description = self._describe_audio_features(features)
                cards.append(InfoCard(
                    id=str(uuid.uuid4()),
                    source=CardSource.SPOTIFY_DATA,
                    title="Audio Analysis",
                    summary=description,
                    track_id=track_id,
                    category="song"
                ))
        
        popularity = track.get("popularity", 0)
        if popularity > 0:
            popularity_desc = "viral hit" if popularity > 80 else "popular" if popularity > 50 else "growing"
            cards.append(InfoCard(
                id=str(uuid.uuid4()),
                source=CardSource.SPOTIFY_DATA,
                title="Popularity Score",
                summary=f"This track has a popularity score of {popularity}/100 on Spotify ({popularity_desc})",
                track_id=track_id,
                category="charts"
            ))
        
        artists = track.get("artists", [])
        if artists:
            artist_id = artists[0].get("id")
            if artist_id:
                related = await self._get_related_artists(artist_id)
                if related:
                    related_names = [a.get("name") for a in related[:6]]
                    cards.append(InfoCard(
                        id=str(uuid.uuid4()),
                        source=CardSource.SPOTIFY_DATA,
                        title="Related Artists",
                        summary=f"Fans also listen to: {', '.join(related_names)}",
                        track_id=track_id,
                        category="similar"
                    ))
        
        return cards
