from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Optional
import asyncio

from app.models import InfoCard, Track
from app.services.card_generator import card_generator

router = APIRouter()

active_card_connections: List[WebSocket] = []


class RegisterTrackRequest(BaseModel):
    track_id: str
    artist: str
    title: str
    album: str = ""


@router.post("/register")
async def register_track(request: RegisterTrackRequest):
    """Register track info for card generation (used when manually selecting a track)."""
    card_generator.set_track_info(
        track_id=request.track_id,
        artist=request.artist,
        title=request.title,
        album=request.album
    )
    print(f"[Cards] Registered track: {request.title} by {request.artist} (ID: {request.track_id})", flush=True)
    return {"status": "registered", "track_id": request.track_id}


@router.websocket("/ws/{track_id}")
async def cards_websocket(websocket: WebSocket, track_id: str):
    """
    WebSocket endpoint for streaming info cards as they're generated.
    Cards appear progressively as data is fetched from various sources.
    """
    await websocket.accept()
    active_card_connections.append(websocket)
    print(f"[WS] Card WebSocket connected for track: {track_id}", flush=True)
    
    try:
        card_count = 0
        async for card in card_generator.generate_cards_stream(track_id):
            card_count += 1
            print(f"[WS] Sending card {card_count}: {card.source.value} - {card.title}", flush=True)
            await websocket.send_json(card.model_dump())
        await websocket.send_json({"done": True, "count": card_count})
        print(f"[WS] Finished streaming {card_count} cards for track: {track_id}", flush=True)
    except WebSocketDisconnect:
        print(f"[WS] Client disconnected for track: {track_id}", flush=True)
        if websocket in active_card_connections:
            active_card_connections.remove(websocket)
    except Exception as e:
        print(f"[WS] Error for track {track_id}: {e}", flush=True)
        await websocket.send_json({"error": str(e)})
        if websocket in active_card_connections:
            active_card_connections.remove(websocket)


@router.get("/{track_id}", response_model=List[InfoCard])
async def get_cards_for_track(track_id: str, source: Optional[str] = None):
    """
    Get all info cards for a track.
    Optionally filter by source (wikipedia, allmusic, web_search, llm).
    """
    cards = await card_generator.get_cards(track_id, source=source)
    return cards


@router.get("/{track_id}/{card_id}", response_model=InfoCard)
async def get_card_detail(track_id: str, card_id: str):
    """Get full details for a specific card."""
    card = await card_generator.get_card_detail(track_id, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Card not found")
    return card


@router.post("/{track_id}/refresh")
async def refresh_cards(track_id: str):
    """Force refresh cards for a track."""
    await card_generator.invalidate_cache(track_id)
    return {"status": "refreshing", "track_id": track_id}
