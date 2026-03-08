import { useEffect, useRef } from 'react';
import { cards as cardsApi } from '../api';
import { InfoCardComponent } from './InfoCard';
import type { Track, InfoCard } from '../types';

interface NowPlayingProps {
  track: Track;
  cards: InfoCard[];
  onNewCard: (card: InfoCard) => void;
  onDismissCard: (cardId: string) => void;
  onBack: () => void;
}

export function NowPlaying({
  track,
  cards,
  onNewCard,
  onDismissCard,
  onBack,
}: NowPlayingProps) {
  const wsRef = useRef<WebSocket | null>(null);
  const connectedTrackRef = useRef<string | null>(null);

  useEffect(() => {
    if (!track.id) return;
    
    // Always connect for a new track
    const isNewTrack = connectedTrackRef.current !== track.id;
    const isConnected = wsRef.current?.readyState === WebSocket.OPEN;
    
    if (!isNewTrack && isConnected) {
      return;
    }

    console.log(`[WS] Connecting for track: ${track.id} (was: ${connectedTrackRef.current})`);
    
    // Close existing connection
    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    
    // Register track with backend first, then connect WebSocket
    const connectCards = async () => {
      try {
        // Register track info with backend to ensure card generator has it
        await cardsApi.registerTrack(track);
        console.log(`[WS] Track registered: ${track.title}`);
      } catch (err) {
        console.error('[WS] Failed to register track:', err);
      }
      
      connectedTrackRef.current = track.id;
      wsRef.current = cardsApi.connectWebSocket(
        track.id,
        (card) => {
          console.log(`[WS] Received card: ${card.source} - ${card.title}`);
          onNewCard(card);
        },
        (error) => console.error('[WS] Error:', error)
      );
    };
    
    connectCards();

    return () => {
      console.log(`[WS] Cleanup for track: ${connectedTrackRef.current}`);
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      connectedTrackRef.current = null;
    };
  }, [track.id, track, onNewCard]);

  // Separate Wikipedia cards (featured at top) from other cards
  const wikipediaCards = cards.filter(c => c.source === 'wikipedia');
  const otherCards = cards.filter(c => c.source !== 'wikipedia');

  const categorizedCards = otherCards.reduce((acc, card) => {
    const cat = card.category;
    if (!acc[cat]) acc[cat] = [];
    acc[cat].push(card);
    return acc;
  }, {} as Record<string, InfoCard[]>);

  // Sort cards within each category: prioritize by source reliability
  const sourceOrder = ['genius', 'musicbrainz', 'discogs', 'lastfm', 'allmusic', 'llm'];
  Object.keys(categorizedCards).forEach(cat => {
    categorizedCards[cat].sort((a, b) => {
      const aIdx = sourceOrder.indexOf(a.source);
      const bIdx = sourceOrder.indexOf(b.source);
      return (aIdx === -1 ? 999 : aIdx) - (bIdx === -1 ? 999 : bIdx);
    });
  });

  const categoryOrder = [
    'song', 'lyrics', 'artist', 'album', 'credits', 
    'samples', 'charts', 'similar', 'concerts', 'videos', 
    'genre', 'history', 'reviews', 'trivia'
  ];

  const sortedCategories = categoryOrder.filter(cat => categorizedCards[cat]);

  const cardsContent = (
    <>
      {cards.length === 0 ? (
        <div className="text-center py-8">
          <div className="w-12 h-12 rounded-full bg-[#252525] flex items-center justify-center mx-auto mb-3">
            <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          </div>
          <p className="text-gray-400 text-sm">Loading liner notes...</p>
          <p className="text-gray-500 text-xs mt-1">Fetching from multiple sources</p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {/* Wikipedia cards pinned at top */}
          {wikipediaCards.length > 0 && (
            <div>
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                Overview
              </h3>
              <div className="flex flex-col gap-3">
                {wikipediaCards.map((card) => (
                  <InfoCardComponent
                    key={card.id}
                    card={card}
                    onDismiss={() => onDismissCard(card.id)}
                  />
                ))}
              </div>
            </div>
          )}
          
          {/* Other cards by category */}
          {sortedCategories.map(category => (
            <div key={category}>
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                {formatCategory(category)}
              </h3>
              <div className="flex flex-col gap-3">
                {categorizedCards[category].map((card) => (
                  <InfoCardComponent
                    key={card.id}
                    card={card}
                    onDismiss={() => onDismissCard(card.id)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );

  return (
    <div className="h-full overflow-auto bg-[#0f0f0f]">
      {/* Critical CSS for immediate layout */}
      <style>{`
        .np-mobile { display: block; }
        .np-desktop { display: none; }
        @media (min-width: 1024px) {
          .np-mobile { display: none !important; }
          .np-desktop { display: flex !important; }
        }
      `}</style>
      
      {/* Back button - always visible */}
      <button
        onClick={onBack}
        style={{ position: 'fixed', top: 8, left: 8, zIndex: 10, width: 36, height: 36, display: 'flex', alignItems: 'center', justifyContent: 'center', borderRadius: '50%', background: 'rgba(0,0,0,0.5)', border: 'none', color: 'white', cursor: 'pointer' }}
      >
        <svg style={{ width: 20, height: 20 }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      {/* Mobile layout: stacked */}
      <div className="np-mobile">
        <div style={{ height: '50vh', minHeight: 320, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 16, gap: 16 }}>
          {track.cover_url ? (
            <img
              src={track.cover_url}
              alt={track.album || ''}
              style={{ width: 280, height: 280, maxWidth: '85vw', maxHeight: '85vw', borderRadius: 12, objectFit: 'cover', boxShadow: '0 12px 40px rgba(0,0,0,0.6)' }}
            />
          ) : (
            <div style={{ width: 280, height: 280, maxWidth: '85vw', maxHeight: '85vw', borderRadius: 12, background: 'linear-gradient(135deg, #1a1a1a, #252525)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg style={{ width: 64, height: 64, color: '#666' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
              </svg>
            </div>
          )}
          <div style={{ textAlign: 'center' }}>
            <h1 style={{ margin: 0, fontSize: 22, fontWeight: 700, color: 'white', lineHeight: 1.3 }}>{track.title}</h1>
            <p style={{ margin: '6px 0 0 0', fontSize: 17, color: '#9ca3af' }}>{track.artist}</p>
            {track.album && <p style={{ margin: '4px 0 0 0', fontSize: 14, color: '#6b7280' }}>{track.album}</p>}
            {cards.length > 0 && (
              <p style={{ margin: '10px 0 0 0', fontSize: 13, color: '#6366f1', fontWeight: 500 }}>{cards.length} liner notes</p>
            )}
          </div>
        </div>
        <div style={{ background: '#1a1a1a', padding: '16px 16px 32px 16px' }}>
          {cardsContent}
        </div>
      </div>

      {/* Desktop layout: side by side */}
      <div className="np-desktop" style={{ minHeight: '100%' }}>
        <div style={{ width: 680, flexShrink: 0, position: 'sticky', top: 0, height: '100vh', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: 32, gap: 20, background: '#0f0f0f' }}>
          {track.cover_url ? (
            <img
              src={track.cover_url}
              alt={track.album || ''}
              style={{ width: 580, height: 580, borderRadius: 12, objectFit: 'cover', boxShadow: '0 12px 40px rgba(0,0,0,0.6)' }}
            />
          ) : (
            <div style={{ width: 580, height: 580, borderRadius: 12, background: 'linear-gradient(135deg, #1a1a1a, #252525)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <svg style={{ width: 80, height: 80, color: '#666' }} fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
              </svg>
            </div>
          )}
          <div style={{ textAlign: 'center' }}>
            <h1 style={{ margin: 0, fontSize: 24, fontWeight: 700, color: 'white', lineHeight: 1.3 }}>{track.title}</h1>
            <p style={{ margin: '8px 0 0 0', fontSize: 18, color: '#9ca3af' }}>{track.artist}</p>
            {track.album && <p style={{ margin: '4px 0 0 0', fontSize: 16, color: '#6b7280' }}>{track.album}</p>}
            {cards.length > 0 && (
              <p style={{ margin: '12px 0 0 0', fontSize: 14, color: '#6366f1', fontWeight: 500 }}>{cards.length} liner notes</p>
            )}
          </div>
        </div>
        <div style={{ flex: 1, background: '#1a1a1a', padding: '24px 24px 48px 24px' }}>
          {cardsContent}
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
