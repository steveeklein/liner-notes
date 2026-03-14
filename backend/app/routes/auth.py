from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse, HTMLResponse
from urllib.parse import quote, unquote
from app.models import LoginRequest, AuthStatus, MusicProvider
from app.services.music import music_service
import os
import html

router = APIRouter()


def get_spotify_redirect_uri(request: Request) -> str:
    """
    Build Spotify redirect URI. Must point at the backend (where callback is handled), not the frontend.
    When the request comes via the Vite proxy (Host: localhost:5173), we still register callback on :8000
    so Spotify redirects to the backend after the user authorizes.
    """
    base_url = os.getenv("BASE_URL")
    if not base_url:
        host = request.headers.get("host", "127.0.0.1:8000")
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


def _get_spotify_auth_url(request: Request, force_login: bool = False, return_to: str = None) -> str:
    """Build Spotify OAuth URL; raises HTTPException if client not configured.
    When force_login, return Spotify logout URL with redirect_uri to our auth URL so user must sign in again.
    return_to is passed as state and used after callback to redirect user to the Liner Notes app."""
    spotify = music_service.providers.get(MusicProvider.SPOTIFY)
    if not spotify or not getattr(spotify, "client_id", None) or not getattr(spotify, "client_secret", None):
        raise HTTPException(
            status_code=503,
            detail="Spotify is not configured. Set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET in backend .env (see README)."
        )
    redirect_uri = get_spotify_redirect_uri(request)
    auth_url = music_service.get_spotify_auth_url(redirect_uri, show_dialog=False, state=return_to)
    if force_login:
        return f"https://accounts.spotify.com/en/logout?redirect_uri={quote(auth_url, safe='')}"
    return auth_url


@router.get("/spotify/login")
async def spotify_login(request: Request):
    """Initiate Spotify OAuth flow (redirect)."""
    auth_url = _get_spotify_auth_url(request)
    return RedirectResponse(url=auth_url)


def _is_safe_redirect_url(next_url: str) -> bool:
    """Allow only Spotify authorize or our frontend (for Sign Out and Continue flows)."""
    if not next_url:
        return False
    frontend = get_frontend_url().rstrip("/")
    return (
        next_url.startswith("https://accounts.spotify.com/authorize")
        or (frontend and (next_url.startswith(frontend + "/") or next_url == frontend))
    )


@router.get("/spotify/clear-session", response_class=HTMLResponse)
async def spotify_clear_session(request: Request, next: str = ""):
    """Load Spotify logout in iframe to clear session, then redirect to next (Spotify auth URL or frontend)."""
    next_url = unquote(next) if next else ""
    if not _is_safe_redirect_url(next_url):
        return HTMLResponse("<body><p>Invalid request.</p></body>", status_code=400)
    # Use data attribute so the URL is preserved (embedding in script would turn & into &amp; and break redirect_uri)
    next_attr = html.escape(next_url, quote=True)
    html_content = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>Logging out...</title></head>
<body style="font-family:sans-serif;background:#0f0f0f;color:#e5e5e5;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;" data-next="{next_attr}">
  <p style="margin:0;">Logging out of Spotify...</p>
  <iframe src="https://accounts.spotify.com/en/logout" style="position:absolute;width:0;height:0;border:0;" title="Spotify logout"></iframe>
  <script>
    setTimeout(function() {{ window.location.href = document.body.getAttribute("data-next"); }}, 2500);
  </script>
</body></html>"""
    return HTMLResponse(html_content)


@router.get("/spotify/url")
async def spotify_auth_url(request: Request, force_login: bool = False, return_to: str = None):
    """Return Spotify authorize URL. After user approves, Spotify redirects to our callback, then we send them to the app.
    If force_login=true (e.g. after Sign Out), returns Spotify logout URL that then redirects to auth so user must log in again."""
    url = _get_spotify_auth_url(request, force_login=force_login, return_to=return_to)
    return {"url": url}


def _safe_return_url(state: str = None) -> str:
    """Return redirect URL: state if it looks like our frontend, else get_frontend_url()."""
    frontend = get_frontend_url().rstrip("/")
    if state and state.startswith(("http://", "https://")):
        if state == frontend or state.startswith(frontend + "/"):
            return state
        if "localhost" in state or "127.0.0.1" in state:
            return state
    return frontend


@router.get("/spotify/callback")
async def spotify_callback(request: Request, code: str = None, error: str = None, state: str = None):
    """Handle Spotify OAuth callback. state is the return_to (Liner Notes URL) we send user to after login."""
    base = _safe_return_url(state).rstrip("/")
    
    if error:
        return RedirectResponse(url=f"{base}/?error=spotify_auth_denied")
    
    if not code:
        return RedirectResponse(url=f"{base}/?error=spotify_no_code")
    
    redirect_uri = get_spotify_redirect_uri(request)
    success = await music_service.complete_spotify_auth(code, redirect_uri)
    
    if success:
        return RedirectResponse(url=f"{base}/?spotify=connected")
    else:
        return RedirectResponse(url=f"{base}/?error=spotify_auth_failed")


@router.post("/logout")
async def logout():
    """Logout from the current music service."""
    await music_service.logout()
    return {"status": "logged_out"}


@router.get("/status", response_model=AuthStatus)
async def get_auth_status():
    """Get current authentication status."""
    return music_service.get_auth_status()
