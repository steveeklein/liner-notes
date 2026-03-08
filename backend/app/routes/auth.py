from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.models import LoginRequest, AuthStatus, MusicProvider
from app.services.music import music_service
import os

router = APIRouter()


def get_spotify_redirect_uri(request: Request) -> str:
    """Build Spotify redirect URI from request."""
    base_url = os.getenv("BASE_URL", str(request.base_url).rstrip("/"))
    return f"{base_url}/api/auth/spotify/callback"


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


@router.get("/spotify/login")
async def spotify_login(request: Request):
    """Initiate Spotify OAuth flow."""
    redirect_uri = get_spotify_redirect_uri(request)
    auth_url = music_service.get_spotify_auth_url(redirect_uri)
    return RedirectResponse(url=auth_url)


@router.get("/spotify/callback")
async def spotify_callback(request: Request, code: str = None, error: str = None):
    """Handle Spotify OAuth callback."""
    if error:
        return RedirectResponse(url="/?error=spotify_auth_denied")
    
    if not code:
        return RedirectResponse(url="/?error=spotify_no_code")
    
    redirect_uri = get_spotify_redirect_uri(request)
    success = await music_service.complete_spotify_auth(code, redirect_uri)
    
    if success:
        return RedirectResponse(url="/?spotify=connected")
    else:
        return RedirectResponse(url="/?error=spotify_auth_failed")


@router.post("/logout")
async def logout():
    """Logout from the current music service."""
    await music_service.logout()
    return {"status": "logged_out"}


@router.get("/status", response_model=AuthStatus)
async def get_auth_status():
    """Get current authentication status."""
    return music_service.get_auth_status()
