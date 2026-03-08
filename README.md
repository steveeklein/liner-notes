# Liner Notes

A Progressive Web App that provides rich contextual information about music as you listen. Connect to your Tidal or Qobuz account, play a song, and discover the story behind the music.

![Liner Notes](https://img.shields.io/badge/PWA-Ready-blue) ![License](https://img.shields.io/badge/license-MIT-green)

## Features

- **Progressive Web App** - Install on your phone's home screen for a native app experience
- **Multiple Music Services** - Connect to Spotify, Tidal, or Qobuz
- **Rich Information Cards** - Real-time streaming of contextual information as you listen
- **14+ Data Sources** including:
  - **Wikipedia** - Artist and album information
  - **Genius** - Lyrics and annotations
  - **MusicBrainz** - Credits and release data
  - **Discogs** - Vinyl releases and catalog info
  - **Last.fm** - Listening stats and similar artists
  - **AllMusic** - Professional biographies and reviews
  - **WhoSampled** - Sample information and cover versions
  - **Billboard** - Chart history and rankings
  - **Setlist.fm** - Concert setlists and tour info
  - **YouTube** - Music videos and interviews
  - **Reddit** - Community discussions
  - **Spotify** - Audio features and popularity data
  - **Web Search** - Additional trivia and stories
  - **AI Insights** - LLM-generated context

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Spotify, Tidal, or Qobuz account

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# For Spotify: Add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET
# Get these at https://developer.spotify.com/dashboard
# Add redirect URI: http://localhost:8000/api/auth/spotify/callback

# Run the server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Visit `http://localhost:5173` on your phone or desktop.

### Installing as PWA

1. Open the app in Chrome/Safari on your phone
2. Tap "Add to Home Screen" (iOS) or the install prompt (Android)
3. The app will now appear as a native app on your home screen

## API Keys (Optional)

Most data sources work without API keys via web scraping. For better reliability and rate limits, you can add:

| Service | Get Key At |
|---------|------------|
| OpenAI | https://platform.openai.com/api-keys |
| Last.fm | https://www.last.fm/api/account/create |
| Genius | https://genius.com/api-clients |
| Discogs | https://www.discogs.com/settings/developers |
| YouTube | https://console.cloud.google.com/apis/credentials |
| Spotify | https://developer.spotify.com/dashboard |
| Setlist.fm | https://api.setlist.fm/docs |
| SerpAPI | https://serpapi.com |

## Architecture

```
liner-notes/
├── backend/                 # Python FastAPI backend
│   ├── app/
│   │   ├── main.py         # FastAPI application
│   │   ├── models.py       # Pydantic models
│   │   ├── routes/         # API endpoints
│   │   └── services/       
│   │       ├── music.py    # Music service integration
│   │       ├── card_generator.py
│   │       └── data_sources/  # Information fetchers
│   └── requirements.txt
│
└── frontend/               # React + TypeScript PWA
    ├── src/
    │   ├── App.tsx         # Main application
    │   ├── components/     # UI components
    │   ├── api.ts          # API client
    │   └── types.ts        # TypeScript types
    └── public/
        └── manifest.json   # PWA manifest
```

## How It Works

1. **Search & Play**: Search for a song and tap to play
2. **WebSocket Connection**: The frontend connects to a WebSocket endpoint
3. **Parallel Fetching**: The backend fetches from all data sources concurrently
4. **Streaming Cards**: As each source responds, cards stream to the UI in real-time
5. **Interactive Cards**: Tap cards to expand, swipe to dismiss, or tap through to source

## Development

```bash
# Run backend in development mode
cd backend && uvicorn app.main:app --reload

# Run frontend in development mode
cd frontend && npm run dev

# Build for production
cd frontend && npm run build
```

## License

MIT
