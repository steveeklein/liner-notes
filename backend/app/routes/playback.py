from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import List
import asyncio
import json

from app.models import Track, PlaybackState, SearchResult
from app.services.music import music_service
from app.services.card_generator import card_generator

router = APIRouter()

active_connections: List[WebSocket] = []


async def broadcast_playback_state(state: PlaybackState):
    """Broadcast playback state to all connected clients."""
    for connection in active_connections:
        try:
            await connection.send_json(state.model_dump())
        except Exception:
            pass


@router.websocket("/ws")
async def playback_websocket(websocket: WebSocket):
    """WebSocket endpoint for real-time playback updates."""
    await websocket.accept()
    active_connections.append(websocket)
    
    try:
        while True:
            state = await music_service.get_playback_state()
            await websocket.send_json(state.model_dump())
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        active_connections.remove(websocket)


@router.get("/state", response_model=PlaybackState)
async def get_playback_state():
    """Get current playback state."""
    state = await music_service.get_playback_state()
    
    # Register track info for card generation
    if state.current_track:
        card_generator.set_track_info(
            track_id=state.current_track.id,
            artist=state.current_track.artist,
            title=state.current_track.title,
            album=state.current_track.album or ""
        )
    
    return state


@router.post("/play/{track_id}")
async def play_track(track_id: str):
    """Play a specific track."""
    success = await music_service.play_track(track_id)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to play track")
    return {"status": "playing", "track_id": track_id}


@router.post("/pause")
async def pause():
    """Pause playback."""
    await music_service.pause()
    return {"status": "paused"}


@router.post("/resume")
async def resume():
    """Resume playback."""
    await music_service.resume()
    return {"status": "playing"}


@router.post("/next")
async def next_track():
    """Skip to next track."""
    await music_service.next_track()
    return {"status": "next"}


@router.post("/previous")
async def previous_track():
    """Go to previous track."""
    await music_service.previous_track()
    return {"status": "previous"}


@router.get("/search", response_model=SearchResult)
async def search(query: str):
    """Search for tracks, albums, and artists."""
    return await music_service.search(query)


@router.get("/playlists")
async def get_playlists():
    """Get user's playlists."""
    return await music_service.get_playlists()


@router.get("/playlist/{playlist_id}/tracks")
async def get_playlist_tracks(playlist_id: str) -> List[Track]:
    """Get tracks in a playlist."""
    return await music_service.get_playlist_tracks(playlist_id)
