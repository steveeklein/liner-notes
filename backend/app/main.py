from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.routes import auth, playback, cards
from app.services.music import music_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await music_service.cleanup()


app = FastAPI(
    title="Liner Notes",
    description="Rich contextual information while you listen to music",
    version="0.1.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(playback.router, prefix="/api/playback", tags=["playback"])
app.include_router(cards.router, prefix="/api/cards", tags=["cards"])


@app.get("/api/health")
async def health_check():
    return {"status": "healthy"}
