from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.models import LoginRequest, AuthStatus, MusicProvider
from app.services.music import music_service
import os

router = APIRouter()


def get_spotify_redirect_uri(request: Request) -> str:
    """Build Spotify redirect URI. Must point at the backend (where callback is handled), not the frontend."""
    base_url = os.getenv("BASE_URL")
    if not base_url:
        host = request.headers.get("host", "127.0.0.1:8000")
        # If request came via frontend proxy (port 5173), use backend port 8000 for callback
        if ":5173" in host:
            host = host.replace(":5173", ":8000")
        if "localhost" in host:
            host = host.replace("localhost", "127.0.0.1")
        base_url = f"http://{host}"
    return f"{base_url.rstrip('/')}/api/auth/spotify/callback"


def get_frontend_url() -> str:
    """Get the frontend URL for redirects after auth."""
    return os.getenv("FRONTEND_URL", "http://localhost:5173")


@router.post("/login", response_model=AuthStatus)
async def login(request: LoginRequest):
    """Login to a music service provider (Tidal/Qobuz only)."""
    if request.provider == MusicProvider.SPOTIFY:
        raise HTTPException(
            status_code=400, 
            detail="Use /api/auth/spotify/login for Spotify authentication"
        )
    
    try:
        success = await music_service.login(
            provider=request.provider,
            username=request.username,
            password=request.password
        )
        if success:
            return AuthStatus(
                authenticated=True,
                provider=request.provider,
                user_name=request.username
            )
        raise HTTPException(status_code=401, detail="Invalid credentials")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


def _get_spotify_auth_url(request: Request) -> str:
    """Build Spotify OAuth URL; raises HTTPException if client not configured."""
    spotify = music_service.providers.get(MusicProvider.SPOTIFY)
    if not spotify or not getattr(spotify, "client_id", None) or not getattr(spotify, "client_secret", None):
        raise HTTPException(
            status_code=503,
            detail="Spotify is not configured. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in backend .env (see README)."
        )
    redirect_uri = get_spotify_redirect_uri(request)
    return music_service.get_spotify_auth_url(redirect_uri)


@router.get("/spotify/login")
async def spotify_login(request: Request):
    """Initiate Spotify OAuth flow (redirect)."""
    auth_url = _get_spotify_auth_url(request)
    return RedirectResponse(url=auth_url)


@router.get("/spotify/url")
async def spotify_auth_url(request: Request):
    """Return Spotify authorize URL. After user approves, Spotify redirects to our callback, then we send them to the app."""
    auth_url = _get_spotify_auth_url(request)
    return {"url": auth_url}


@router.get("/spotify/callback")
async def spotify_callback(request: Request, code: str = None, error: str = None):
    """Handle Spotify OAuth callback."""
    frontend_url = get_frontend_url()
    
    if error:
        return RedirectResponse(url=f"{frontend_url}/?error=spotify_auth_denied")
    
    if not code:
        return RedirectResponse(url=f"{frontend_url}/?error=spotify_no_code")
    
    redirect_uri = get_spotify_redirect_uri(request)
    success = await music_service.complete_spotify_auth(code, redirect_uri)
    
    if success:
        return RedirectResponse(url=f"{frontend_url}/?spotify=connected")
    else:
        return RedirectResponse(url=f"{frontend_url}/?error=spotify_auth_failed")


@router.post("/logout")
async def logout():
    """Logout from the current music service."""
    await music_service.logout()
    return {"status": "logged_out"}


@router.get("/status", response_model=AuthStatus)
async def get_auth_status():
    """Get current authentication status."""
    return music_service.get_auth_status()
