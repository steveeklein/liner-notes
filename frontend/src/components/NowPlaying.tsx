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
          {sortedCategories.map(category => (
            <div key={category}>
              <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
                {formatCategory(category)}
              </h3>
              <div className="flex flex-col gap-3">
                {categorizedCards[category].map((card, index) => (
                  <InfoCardComponent
                    key={card.id}
                    card={card}
                    onDismiss={() => onDismissCard(card.id)}
                    style={{ animationDelay: `${index * 50}ms` }}
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
      {/* Back button - always visible */}
      <button
        onClick={onBack}
        className="fixed top-2 left-2 z-10 w-9 h-9 flex items-center justify-center rounded-full bg-black/50 border-none text-white cursor-pointer hover:bg-black/70 transition-colors"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 19l-7-7 7-7" />
        </svg>
      </button>

      {/* Mobile layout: stacked */}
      <div className="lg:hidden">
        {/* Album section - centered */}
        <div className="h-[50vh] min-h-[300px] flex flex-col items-center justify-center p-4 gap-4">
          {/* Album art */}
          {track.cover_url ? (
            <img
              src={track.cover_url}
              alt={track.album || ''}
              className="w-[min(calc(60vh-120px),90vw)] h-[min(calc(60vh-120px),90vw)] min-w-[242px] min-h-[242px] max-w-[425px] max-h-[425px] rounded-xl object-cover shadow-2xl"
            />
          ) : (
            <div className="w-[min(calc(60vh-120px),90vw)] h-[min(calc(60vh-120px),90vw)] min-w-[242px] min-h-[242px] max-w-[425px] max-h-[425px] rounded-xl bg-gradient-to-br from-[#1a1a1a] to-[#252525] flex items-center justify-center">
              <svg className="w-16 h-16 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
              </svg>
            </div>
          )}
          
          {/* Track info */}
          <div className="text-center">
            <h1 className="m-0 text-[22px] font-bold text-white leading-tight">{track.title}</h1>
            <p className="mt-1.5 text-[17px] text-gray-400">{track.artist}</p>
            {track.album && <p className="mt-1 text-sm text-gray-500">{track.album}</p>}
            {cards.length > 0 && (
              <p className="mt-2.5 text-[13px] text-indigo-500 font-medium">{cards.length} liner notes</p>
            )}
          </div>
        </div>

        {/* Cards section */}
        <div className="bg-[#1a1a1a] p-4 pb-8">
          {cardsContent}
        </div>
      </div>

      {/* Desktop layout: side by side */}
      <div className="hidden lg:flex min-h-full">
        {/* Left sidebar - Album */}
        <div className="w-[485px] xl:w-[550px] shrink-0 sticky top-0 h-screen flex flex-col items-center justify-center p-8 gap-5 bg-[#0f0f0f]">
          {/* Album art */}
          {track.cover_url ? (
            <img
              src={track.cover_url}
              alt={track.album || ''}
              className="w-[387px] xl:w-[436px] h-[387px] xl:h-[436px] rounded-xl object-cover shadow-2xl"
            />
          ) : (
            <div className="w-[387px] xl:w-[436px] h-[387px] xl:h-[436px] rounded-xl bg-gradient-to-br from-[#1a1a1a] to-[#252525] flex items-center justify-center">
              <svg className="w-20 h-20 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
              </svg>
            </div>
          )}
          
          {/* Track info */}
          <div className="text-center">
            <h1 className="m-0 text-2xl font-bold text-white leading-tight">{track.title}</h1>
            <p className="mt-2 text-lg text-gray-400">{track.artist}</p>
            {track.album && <p className="mt-1 text-base text-gray-500">{track.album}</p>}
            {cards.length > 0 && (
              <p className="mt-3 text-sm text-indigo-500 font-medium">{cards.length} liner notes</p>
            )}
          </div>
        </div>

        {/* Right content - Cards */}
        <div className="flex-1 bg-[#1a1a1a] p-6 pb-12">
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
