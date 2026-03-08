from typing import Optional, List
import asyncio
import os
import base64
from abc import ABC, abstractmethod
import httpx
from dotenv import load_dotenv

from app.models import (
    MusicProvider, AuthStatus, Track, PlaybackState, SearchResult
)

load_dotenv()


class MusicProviderInterface(ABC):
    """Abstract interface for music providers."""
    
    @abstractmethod
    async def login(self, username: str, password: str) -> bool:
        pass
    
    @abstractmethod
    async def logout(self) -> None:
        pass
    
    @abstractmethod
    async def get_playback_state(self) -> PlaybackState:
        pass
    
    @abstractmethod
    async def play_track(self, track_id: str) -> bool:
        pass
    
    @abstractmethod
    async def pause(self) -> None:
        pass
    
    @abstractmethod
    async def resume(self) -> None:
        pass
    
    @abstractmethod
    async def search(self, query: str) -> SearchResult:
        pass


class TidalProvider(MusicProviderInterface):
    """Tidal music provider implementation."""
    
    def __init__(self):
        self.session = None
        self.current_track: Optional[Track] = None
        self.is_playing = False
        self.queue: List[Track] = []
        self.queue_index = 0
    
    async def login(self, username: str, password: str) -> bool:
        try:
            import tidalapi
            self.session = tidalapi.Session()
            return self.session.login(username, password)
        except Exception as e:
            print(f"Tidal login error: {e}")
            return False
    
    async def logout(self) -> None:
        self.session = None
        self.current_track = None
        self.is_playing = False
    
    async def get_playback_state(self) -> PlaybackState:
        return PlaybackState(
            is_playing=self.is_playing,
            current_track=self.current_track,
            position=0
        )
    
    async def play_track(self, track_id: str) -> bool:
        if not self.session:
            return False
        
        try:
            track = self.session.track(track_id)
            self.current_track = Track(
                id=str(track.id),
                title=track.name,
                artist=track.artist.name,
                album=track.album.name if track.album else "",
                duration=track.duration,
                cover_url=track.album.image(640) if track.album else None,
                provider=MusicProvider.TIDAL
            )
            self.is_playing = True
            return True
        except Exception as e:
            print(f"Error playing track: {e}")
            return False
    
    async def pause(self) -> None:
        self.is_playing = False
    
    async def resume(self) -> None:
        self.is_playing = True
    
    async def next_track(self) -> None:
        if self.queue and self.queue_index < len(self.queue) - 1:
            self.queue_index += 1
            self.current_track = self.queue[self.queue_index]
    
    async def previous_track(self) -> None:
        if self.queue and self.queue_index > 0:
            self.queue_index -= 1
            self.current_track = self.queue[self.queue_index]
    
    async def search(self, query: str) -> SearchResult:
        if not self.session:
            return SearchResult(tracks=[], albums=[], artists=[])
        
        try:
            results = self.session.search(query)
            tracks = [
                Track(
                    id=str(t.id),
                    title=t.name,
                    artist=t.artist.name,
                    album=t.album.name if t.album else "",
                    duration=t.duration,
                    cover_url=t.album.image(320) if t.album else None,
                    provider=MusicProvider.TIDAL
                )
                for t in results.tracks[:20]
            ]
            return SearchResult(
                tracks=tracks,
                albums=[{"id": str(a.id), "name": a.name} for a in results.albums[:10]],
                artists=[{"id": str(a.id), "name": a.name} for a in results.artists[:10]]
            )
        except Exception as e:
            print(f"Search error: {e}")
            return SearchResult(tracks=[], albums=[], artists=[])
    
    async def get_playlists(self) -> List[dict]:
        if not self.session:
            return []
        
        try:
            playlists = self.session.user.playlists()
            return [
                {"id": str(p.id), "name": p.name, "track_count": p.num_tracks}
                for p in playlists
            ]
        except Exception:
            return []
    
    async def get_playlist_tracks(self, playlist_id: str) -> List[Track]:
        if not self.session:
            return []
        
        try:
            playlist = self.session.playlist(playlist_id)
            return [
                Track(
                    id=str(t.id),
                    title=t.name,
                    artist=t.artist.name,
                    album=t.album.name if t.album else "",
                    duration=t.duration,
                    cover_url=t.album.image(320) if t.album else None,
                    provider=MusicProvider.TIDAL
                )
                for t in playlist.tracks()
            ]
        except Exception:
            return []


class SpotifyProvider(MusicProviderInterface):
    """
    Spotify music provider implementation.
    Uses Spotify Web API to control playback on the user's active device.
    """
    
    BASE_URL = "https://api.spotify.com/v1"
    AUTH_URL = "https://accounts.spotify.com/api/token"
    
    def __init__(self):
        self.client_id = os.getenv("SPOTIFY_CLIENT_ID")
        self.client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.current_track: Optional[Track] = None
        self.is_playing = False
        self.user_name: Optional[str] = None
    
    def get_auth_url(self, redirect_uri: str) -> str:
        """Generate Spotify OAuth authorization URL."""
        from urllib.parse import urlencode
        
        scopes = [
            "user-read-playback-state",
            "user-modify-playback-state",
            "user-read-currently-playing",
            "playlist-read-private",
            "playlist-read-collaborative",
            "user-library-read",
            "streaming",
        ]
        params = {
            "client_id": self.client_id,
            "response_type": "code",
            "redirect_uri": redirect_uri,
            "scope": " ".join(scopes),
            "show_dialog": "true",
        }
        return f"https://accounts.spotify.com/authorize?{urlencode(params)}"
    
    async def exchange_code(self, code: str, redirect_uri: str) -> bool:
        """Exchange authorization code for access token."""
        import sys
        print(f"[Spotify] Exchanging code with redirect_uri: {redirect_uri}", flush=True)
        try:
            credentials = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.AUTH_URL,
                    data={
                        "grant_type": "authorization_code",
                        "code": code,
                        "redirect_uri": redirect_uri,
                    },
                    headers={
                        "Authorization": f"Basic {credentials}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    timeout=10.0
                )
                
                print(f"[Spotify] Token exchange response: {response.status_code}", flush=True)
                
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data.get("access_token")
                    self.refresh_token = data.get("refresh_token")
                    print(f"[Spotify] Got access_token: {bool(self.access_token)}", flush=True)
                    
                    user_info = await self._get_user_profile()
                    print(f"[Spotify] User info: {user_info}", flush=True)
                    if user_info:
                        self.user_name = user_info.get("display_name") or user_info.get("id")
                    
                    return True
                    
                print(f"[Spotify] Token exchange failed: {response.text}", flush=True)
                return False
        except Exception as e:
            print(f"[Spotify] Exchange error: {e}", flush=True)
            return False
    
    async def _refresh_access_token(self) -> bool:
        """Refresh the access token."""
        if not self.refresh_token:
            return False
        
        try:
            credentials = base64.b64encode(
                f"{self.client_id}:{self.client_secret}".encode()
            ).decode()
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.AUTH_URL,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": self.refresh_token,
                    },
                    headers={
                        "Authorization": f"Basic {credentials}",
                        "Content-Type": "application/x-www-form-urlencoded",
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    self.access_token = data.get("access_token")
                    if data.get("refresh_token"):
                        self.refresh_token = data.get("refresh_token")
                    return True
        except Exception as e:
            print(f"Spotify refresh error: {e}")
        
        return False
    
    async def _api_request(self, method: str, endpoint: str, **kwargs) -> dict | None:
        """Make an authenticated API request."""
        if not self.access_token:
            print(f"[Spotify] API request failed: No access token for {endpoint}", flush=True)
            return None
        print(f"[Spotify] API request: {method} {endpoint}", flush=True)
        
        headers = {"Authorization": f"Bearer {self.access_token}"}
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method,
                    f"{self.BASE_URL}{endpoint}",
                    headers=headers,
                    timeout=10.0,
                    **kwargs
                )
                
                if response.status_code == 401:
                    if await self._refresh_access_token():
                        headers = {"Authorization": f"Bearer {self.access_token}"}
                        response = await client.request(
                            method,
                            f"{self.BASE_URL}{endpoint}",
                            headers=headers,
                            timeout=10.0,
                            **kwargs
                        )
                
                print(f"[Spotify] API response: {response.status_code}", flush=True)
                if response.status_code in (200, 201):
                    data = response.json() if response.text else {}
                    print(f"[Spotify] API data keys: {list(data.keys()) if isinstance(data, dict) else 'not a dict'}", flush=True)
                    return data
                elif response.status_code == 204:
                    return {}
                else:
                    print(f"[Spotify] API error response: {response.text[:500]}", flush=True)
                    
        except Exception as e:
            print(f"[Spotify] API error: {e}", flush=True)
        
        return None
    
    async def _get_user_profile(self) -> dict | None:
        """Get current user's profile."""
        return await self._api_request("GET", "/me")
    
    async def login(self, username: str, password: str) -> bool:
        """
        For Spotify, username/password login isn't supported.
        Use exchange_code() after OAuth redirect instead.
        This returns True if already authenticated.
        """
        return self.access_token is not None
    
    async def logout(self) -> None:
        self.access_token = None
        self.refresh_token = None
        self.current_track = None
        self.is_playing = False
        self.user_name = None
    
    async def get_playback_state(self) -> PlaybackState:
        """Get current playback state from Spotify."""
        # Try currently-playing endpoint first (works more reliably)
        data = await self._api_request("GET", "/me/player/currently-playing")
        
        if data and data.get("item"):
            item = data["item"]
            artists = ", ".join(a["name"] for a in item.get("artists", []))
            album = item.get("album", {})
            
            images = album.get("images", [])
            cover_url = images[0]["url"] if images else None
            
            self.current_track = Track(
                id=item["id"],
                title=item["name"],
                artist=artists,
                album=album.get("name", ""),
                duration=item.get("duration_ms", 0) // 1000,
                cover_url=cover_url,
                provider=MusicProvider.SPOTIFY
            )
            self.is_playing = data.get("is_playing", False)
            
            return PlaybackState(
                is_playing=self.is_playing,
                current_track=self.current_track,
                position=data.get("progress_ms", 0) // 1000
            )
        
        return PlaybackState(
            is_playing=self.is_playing,
            current_track=self.current_track,
            position=0
        )
    
    async def play_track(self, track_id: str) -> bool:
        """Play a track on the user's active Spotify device."""
        result = await self._api_request(
            "PUT",
            "/me/player/play",
            json={"uris": [f"spotify:track:{track_id}"]}
        )
        
        if result is not None:
            await self.get_playback_state()
            return True
        return False
    
    async def pause(self) -> None:
        await self._api_request("PUT", "/me/player/pause")
        self.is_playing = False
    
    async def resume(self) -> None:
        await self._api_request("PUT", "/me/player/play")
        self.is_playing = True
    
    async def next_track(self) -> None:
        await self._api_request("POST", "/me/player/next")
        await asyncio.sleep(0.5)
        await self.get_playback_state()
    
    async def previous_track(self) -> None:
        await self._api_request("POST", "/me/player/previous")
        await asyncio.sleep(0.5)
        await self.get_playback_state()
    
    async def search(self, query: str) -> SearchResult:
        data = await self._api_request(
            "GET",
            "/search",
            params={"q": query, "type": "track,album,artist", "limit": 20}
        )
        
        if not data:
            return SearchResult(tracks=[], albums=[], artists=[])
        
        tracks = []
        for item in data.get("tracks", {}).get("items", []):
            artists = ", ".join(a["name"] for a in item.get("artists", []))
            album = item.get("album", {})
            images = album.get("images", [])
            
            tracks.append(Track(
                id=item["id"],
                title=item["name"],
                artist=artists,
                album=album.get("name", ""),
                duration=item.get("duration_ms", 0) // 1000,
                cover_url=images[0]["url"] if images else None,
                provider=MusicProvider.SPOTIFY
            ))
        
        albums = [
            {"id": a["id"], "name": a["name"]}
            for a in data.get("albums", {}).get("items", [])
        ]
        
        artists = [
            {"id": a["id"], "name": a["name"]}
            for a in data.get("artists", {}).get("items", [])
        ]
        
        return SearchResult(tracks=tracks, albums=albums, artists=artists)
    
    async def get_playlists(self) -> List[dict]:
        data = await self._api_request("GET", "/me/playlists", params={"limit": 50})
        
        if not data:
            return []
        
        return [
            {
                "id": p["id"],
                "name": p["name"],
                "track_count": p.get("tracks", {}).get("total", 0)
            }
            for p in data.get("items", [])
        ]
    
    async def get_playlist_tracks(self, playlist_id: str) -> List[Track]:
        data = await self._api_request(
            "GET",
            f"/playlists/{playlist_id}/tracks",
            params={"limit": 100}
        )
        
        if not data:
            return []
        
        tracks = []
        for item in data.get("items", []):
            track = item.get("track")
            if not track or track.get("type") != "track":
                continue
            
            artists = ", ".join(a["name"] for a in track.get("artists", []))
            album = track.get("album", {})
            images = album.get("images", [])
            
            tracks.append(Track(
                id=track["id"],
                title=track["name"],
                artist=artists,
                album=album.get("name", ""),
                duration=track.get("duration_ms", 0) // 1000,
                cover_url=images[0]["url"] if images else None,
                provider=MusicProvider.SPOTIFY
            ))
        
        return tracks
    
    async def get_saved_tracks(self, limit: int = 50) -> List[Track]:
        """Get user's liked songs."""
        data = await self._api_request(
            "GET",
            "/me/tracks",
            params={"limit": limit}
        )
        
        if not data:
            return []
        
        tracks = []
        for item in data.get("items", []):
            track = item.get("track")
            if not track:
                continue
            
            artists = ", ".join(a["name"] for a in track.get("artists", []))
            album = track.get("album", {})
            images = album.get("images", [])
            
            tracks.append(Track(
                id=track["id"],
                title=track["name"],
                artist=artists,
                album=album.get("name", ""),
                duration=track.get("duration_ms", 0) // 1000,
                cover_url=images[0]["url"] if images else None,
                provider=MusicProvider.SPOTIFY
            ))
        
        return tracks


class QobuzProvider(MusicProviderInterface):
    """Qobuz music provider implementation."""
    
    def __init__(self):
        self.session = None
        self.current_track: Optional[Track] = None
        self.is_playing = False
        self.app_id = None
        self.user_auth_token = None
    
    async def login(self, username: str, password: str) -> bool:
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://www.qobuz.com/api.json/0.2/user/login",
                    params={
                        "email": username,
                        "password": password,
                        "app_id": self.app_id or "285473059"
                    }
                )
                if response.status_code == 200:
                    data = response.json()
                    self.user_auth_token = data.get("user_auth_token")
                    return True
                return False
        except Exception as e:
            print(f"Qobuz login error: {e}")
            return False
    
    async def logout(self) -> None:
        self.session = None
        self.user_auth_token = None
        self.current_track = None
        self.is_playing = False
    
    async def get_playback_state(self) -> PlaybackState:
        return PlaybackState(
            is_playing=self.is_playing,
            current_track=self.current_track,
            position=0
        )
    
    async def play_track(self, track_id: str) -> bool:
        self.is_playing = True
        return True
    
    async def pause(self) -> None:
        self.is_playing = False
    
    async def resume(self) -> None:
        self.is_playing = True
    
    async def search(self, query: str) -> SearchResult:
        if not self.user_auth_token:
            return SearchResult(tracks=[], albums=[], artists=[])
        
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "https://www.qobuz.com/api.json/0.2/catalog/search",
                    params={
                        "query": query,
                        "limit": 20,
                        "app_id": self.app_id or "285473059"
                    },
                    headers={"X-User-Auth-Token": self.user_auth_token}
                )
                if response.status_code == 200:
                    data = response.json()
                    tracks = [
                        Track(
                            id=str(t["id"]),
                            title=t["title"],
                            artist=t.get("performer", {}).get("name", "Unknown"),
                            album=t.get("album", {}).get("title", ""),
                            duration=t.get("duration", 0),
                            cover_url=t.get("album", {}).get("image", {}).get("large"),
                            provider=MusicProvider.QOBUZ
                        )
                        for t in data.get("tracks", {}).get("items", [])
                    ]
                    return SearchResult(tracks=tracks, albums=[], artists=[])
        except Exception as e:
            print(f"Qobuz search error: {e}")
        
        return SearchResult(tracks=[], albums=[], artists=[])


class MusicService:
    """Main music service that manages providers."""
    
    def __init__(self):
        self.providers = {
            MusicProvider.SPOTIFY: SpotifyProvider(),
            MusicProvider.TIDAL: TidalProvider(),
            MusicProvider.QOBUZ: QobuzProvider(),
        }
        self.active_provider: Optional[MusicProvider] = None
        self.username: Optional[str] = None
    
    def get_spotify_auth_url(self, redirect_uri: str) -> str:
        """Get Spotify OAuth authorization URL."""
        spotify = self.providers[MusicProvider.SPOTIFY]
        return spotify.get_auth_url(redirect_uri)
    
    async def complete_spotify_auth(self, code: str, redirect_uri: str) -> bool:
        """Complete Spotify OAuth flow with authorization code."""
        spotify = self.providers[MusicProvider.SPOTIFY]
        success = await spotify.exchange_code(code, redirect_uri)
        if success:
            self.active_provider = MusicProvider.SPOTIFY
            self.username = spotify.user_name
        return success
    
    def _get_active_provider(self) -> Optional[MusicProviderInterface]:
        if self.active_provider:
            return self.providers[self.active_provider]
        return None
    
    async def login(self, provider: MusicProvider, username: str, password: str) -> bool:
        success = await self.providers[provider].login(username, password)
        if success:
            self.active_provider = provider
            self.username = username
        return success
    
    async def logout(self) -> None:
        if provider := self._get_active_provider():
            await provider.logout()
        self.active_provider = None
        self.username = None
    
    def get_auth_status(self) -> AuthStatus:
        return AuthStatus(
            authenticated=self.active_provider is not None,
            provider=self.active_provider,
            user_name=self.username
        )
    
    async def get_playback_state(self) -> PlaybackState:
        if provider := self._get_active_provider():
            return await provider.get_playback_state()
        return PlaybackState(is_playing=False, current_track=None)
    
    async def play_track(self, track_id: str) -> bool:
        if provider := self._get_active_provider():
            return await provider.play_track(track_id)
        return False
    
    async def pause(self) -> None:
        if provider := self._get_active_provider():
            await provider.pause()
    
    async def resume(self) -> None:
        if provider := self._get_active_provider():
            await provider.resume()
    
    async def next_track(self) -> None:
        if provider := self._get_active_provider():
            if hasattr(provider, 'next_track'):
                await provider.next_track()
    
    async def previous_track(self) -> None:
        if provider := self._get_active_provider():
            if hasattr(provider, 'previous_track'):
                await provider.previous_track()
    
    async def search(self, query: str) -> SearchResult:
        if provider := self._get_active_provider():
            return await provider.search(query)
        return SearchResult(tracks=[], albums=[], artists=[])
    
    async def get_playlists(self) -> List[dict]:
        if provider := self._get_active_provider():
            if hasattr(provider, 'get_playlists'):
                return await provider.get_playlists()
        return []
    
    async def get_playlist_tracks(self, playlist_id: str) -> List[Track]:
        if provider := self._get_active_provider():
            if hasattr(provider, 'get_playlist_tracks'):
                return await provider.get_playlist_tracks(playlist_id)
        return []
    
    async def cleanup(self) -> None:
        await self.logout()


music_service = MusicService()
