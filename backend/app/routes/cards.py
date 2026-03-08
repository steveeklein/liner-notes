from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from typing import List, Optional
import asyncio

from app.models import InfoCard, Track
from app.services.card_generator import card_generator

router = APIRouter()

active_card_connections: List[WebSocket] = []


@router.websocket("/ws/{track_id}")
async def cards_websocket(websocket: WebSocket, track_id: str):
    """
    WebSocket endpoint for streaming info cards as they're generated.
    Cards appear progressively as data is fetched from various sources.
    """
    await websocket.accept()
    active_card_connections.append(websocket)
    
    try:
        async for card in card_generator.generate_cards_stream(track_id):
            await websocket.send_json(card.model_dump())
    except WebSocketDisconnect:
        active_card_connections.remove(websocket)
    except Exception as e:
        await websocket.send_json({"error": str(e)})
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
