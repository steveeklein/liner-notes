import { useEffect, useRef } from 'react';
import { cards as cardsApi } from '../api';
import { InfoCardComponent } from './InfoCard';
import type { Track, InfoCard } from '../types';

interface NowPlayingProps {
  track: Track;
  cards: InfoCard[];
  onNewCard: (card: InfoCard) => void;
  onCardSelect: (card: InfoCard) => void;
  onDismissCard: (cardId: string) => void;
  onBack: () => void;
}

export function NowPlaying({
  track,
  cards,
  onNewCard,
  onCardSelect,
  onDismissCard,
  onBack,
}: NowPlayingProps) {
  const wsRef = useRef<WebSocket | null>(null);
  const connectedTrackRef = useRef<string | null>(null);

  useEffect(() => {
    if (!track.id) return;
    
    // Prevent reconnecting to same track
    if (connectedTrackRef.current === track.id && wsRef.current?.readyState === WebSocket.OPEN) {
      return;
    }

    // Close existing connection
    wsRef.current?.close();
    
    connectedTrackRef.current = track.id;
    wsRef.current = cardsApi.connectWebSocket(
      track.id,
      onNewCard,
      (error) => console.error('WebSocket error:', error)
    );

    return () => {
      wsRef.current?.close();
      wsRef.current = null;
    };
  }, [track.id, onNewCard]);

  const categorizedCards = cards.reduce((acc, card) => {
    const cat = card.category;
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(card);
    return acc;
  }, {} as Record<string, InfoCard[]>);

  const categoryOrder = [
    'song', 'lyrics', 'artist', 'album', 'credits', 
    'samples', 'charts', 'similar', 'concerts', 'videos', 
    'genre', 'history', 'reviews', 'trivia'
  ];

  const sortedCategories = categoryOrder.filter(cat => categorizedCards[cat]);

  return (
    <div className="h-full flex flex-col animate-slide-up overflow-hidden">
      {/* Header with back button */}
      <div className="flex-shrink-0 px-4 py-2 flex items-center">
        <button
          onClick={onBack}
          className="w-10 h-10 -ml-2 flex items-center justify-center haptic rounded-full active:bg-white/10"
        >
          <svg className="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
          </svg>
        </button>
        <span className="text-sm text-gray-400 ml-2">Now Playing</span>
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-y-auto">
        {/* Album Art and Track Info */}
        <div className="px-6 pb-4">
          <div className="flex items-start gap-4">
            {track.cover_url ? (
              <img
                src={track.cover_url}
                alt={track.album}
                className="w-24 h-24 rounded-xl object-cover shadow-lg flex-shrink-0"
              />
            ) : (
              <div className="w-24 h-24 rounded-xl bg-gradient-to-br from-[#1a1a1a] to-[#252525] flex items-center justify-center flex-shrink-0">
                <svg className="w-10 h-10 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
                </svg>
              </div>
            )}
            
            <div className="flex-1 min-w-0 pt-1">
              <h1 className="text-xl font-bold truncate">{track.title}</h1>
              <p className="text-gray-400 truncate">{track.artist}</p>
              {track.album && (
                <p className="text-gray-500 text-sm truncate">{track.album}</p>
              )}
            </div>
          </div>
        </div>

        {/* Cards Section */}
        <div className="bg-[#1a1a1a] rounded-t-3xl min-h-[50vh]">
          <div className="sheet-handle" />
          
          <div className="px-4 pb-8">
            <h2 className="text-lg font-semibold mb-4">
              Liner Notes
              {cards.length > 0 && (
                <span className="text-gray-500 font-normal ml-2">({cards.length})</span>
              )}
            </h2>

            {cards.length === 0 ? (
              <div className="text-center py-12">
                <div className="w-16 h-16 rounded-full bg-[#252525] flex items-center justify-center mx-auto mb-4">
                  <div className="w-6 h-6 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
                </div>
                <p className="text-gray-400">Loading liner notes...</p>
                <p className="text-gray-500 text-sm mt-1">
                  Fetching from multiple sources
                </p>
              </div>
            ) : (
              <div className="space-y-6">
                {sortedCategories.map(category => (
                  <div key={category}>
                    <h3 className="text-sm font-medium text-gray-400 uppercase tracking-wider mb-3">
                      {formatCategory(category)}
                    </h3>
                    <div className="space-y-3">
                      {categorizedCards[category].map((card, index) => (
                        <InfoCardComponent
                          key={card.id}
                          card={card}
                          onClick={() => onCardSelect(card)}
                          onDismiss={() => onDismissCard(card.id)}
                          style={{ animationDelay: `${index * 50}ms` }}
                        />
                      ))}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function formatCategory(category: string): string {
  const labels: Record<string, string> = {
    song: 'About This Song',
    lyrics: 'Lyrics & Meaning',
    artist: 'About the Artist',
    album: 'About the Album',
    credits: 'Credits',
    samples: 'Samples & Covers',
    charts: 'Charts & Stats',
    similar: 'Similar Music',
    concerts: 'Live & Tours',
    videos: 'Videos',
    genre: 'Genre & Style',
    history: 'History',
    reviews: 'Reviews',
    trivia: 'Trivia & More',
  };
  return labels[category] || category;
}
