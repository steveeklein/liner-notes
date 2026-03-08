from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse
from app.models import LoginRequest, AuthStatus, MusicProvider
from app.services.music import music_service
import os

router = APIRouter()


def get_spotify_redirect_uri(request: Request) -> str:
    """Build Spotify redirect URI from request."""
    base_url = os.getenv("BASE_URL")
    if not base_url:
        # Use 127.0.0.1 for local development (Spotify requires this format)
        host = request.headers.get("host", "127.0.0.1:8000")
        if "localhost" in host:
            host = host.replace("localhost", "127.0.0.1")
        base_url = f"http://{host}"
    return f"{base_url}/api/auth/spotify/callback"


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


@router.get("/spotify/login")
async def spotify_login(request: Request):
    """Initiate Spotify OAuth flow."""
    redirect_uri = get_spotify_redirect_uri(request)
    auth_url = music_service.get_spotify_auth_url(redirect_uri)
    return RedirectResponse(url=auth_url)


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
