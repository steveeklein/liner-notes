import { useEffect, useRef, useState } from 'react';
import { cards as cardsApi } from '../api';
import { InfoCardComponent } from './InfoCard';
import type { Track, InfoCard } from '../types';

interface NowPlayingProps {
  track: Track;
  cards: InfoCard[];
  onNewCard: (card: InfoCard) => void;
  onDismissCard: (cardId: string) => void;
  onRefreshSection?: (sectionId: string) => Promise<void>;
}

export function NowPlaying({
  track,
  cards,
  onNewCard,
  onDismissCard,
  onRefreshSection,
}: NowPlayingProps) {
  const wsRef = useRef<WebSocket | null>(null);
  const connectedTrackRef = useRef<string | null>(null);
  const [streamDone, setStreamDone] = useState(false);
  const [refreshingSection, setRefreshingSection] = useState<string | null>(null);

  useEffect(() => {
    if (!track.id) return;
    const trackId = track.id;
    setStreamDone(false);

    const isNewTrack = connectedTrackRef.current !== trackId;
    const isConnected = wsRef.current?.readyState === WebSocket.OPEN;

    if (!isNewTrack && isConnected) {
      return;
    }

    console.log(`[WS] Connecting for track: ${trackId} (was: ${connectedTrackRef.current})`);

    if (wsRef.current) {
      wsRef.current.close();
      wsRef.current = null;
    }
    connectedTrackRef.current = trackId;

    const connectCards = async () => {
      try {
        await cardsApi.registerTrack(track);
        console.log(`[WS] Track registered: ${track.title}`);
      } catch (err) {
        console.error('[WS] Failed to register track:', err);
      }
      if (connectedTrackRef.current !== trackId) return;
      wsRef.current = cardsApi.connectWebSocket(
        trackId,
        (card) => {
          if (connectedTrackRef.current === trackId) onNewCard(card);
        },
        (error) => console.error('[WS] Error:', error),
        (count) => {
          if (connectedTrackRef.current === trackId) setStreamDone(true);
        }
      );
    };

    connectCards();

    return () => {
      if (wsRef.current) {
        wsRef.current.close();
        wsRef.current = null;
      }
      connectedTrackRef.current = null;
    };
  }, [track.id, track, onNewCard]);

  // Define sections in display order
  const sections = [
    { id: 'artist', label: 'About the Artist' },
    { id: 'album', label: 'About the Album' },
    { id: 'song', label: 'About This Song' },
    { id: 'discussions', label: 'Discussions' },
  ] as const;

  // Sort cards by source reliability within each section
  const sourceOrder = ['wikipedia', 'genius', 'musicbrainz', 'discogs', 'lastfm', 'allmusic', 'llm', 'reddit'];
  const sortedCards = [...cards].sort((a, b) => {
    const aIdx = sourceOrder.indexOf(a.source);
    const bIdx = sourceOrder.indexOf(b.source);
    return (aIdx === -1 ? 999 : aIdx) - (bIdx === -1 ? 999 : bIdx);
  });

  // Get cards for each section using the backend-assigned section field
  const getCardsForSection = (sectionId: string): InfoCard[] => {
    return sortedCards.filter(card => card.section === sectionId);
  };

  const cardsContent = (
    <>
      {cards.length === 0 && !streamDone ? (
        <div className="text-center py-8">
          <div className="w-12 h-12 rounded-full bg-[#252525] flex items-center justify-center mx-auto mb-3">
            <div className="w-5 h-5 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin" />
          </div>
          <p className="text-gray-400 text-sm">Loading liner notes...</p>
          <p className="text-gray-500 text-xs mt-1">Fetching from multiple sources</p>
        </div>
      ) : cards.length === 0 && streamDone ? (
        <div className="text-center py-8 px-4">
          <p className="text-gray-400 text-sm">No liner notes found for this track.</p>
          <p className="text-gray-500 text-xs mt-2 max-w-sm mx-auto">
            Add API keys in backend <code className="bg-[#252525] px-1 rounded">.env</code> for more sources (Last.fm, Genius, GROQ, etc.). See README.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-4">
          {sections.map(section => {
            const sectionCards = getCardsForSection(section.id);
            const showEmptyNote = streamDone && sectionCards.length === 0 && (section.id === 'album' || section.id === 'song');
            if (sectionCards.length === 0 && !showEmptyNote) return null;

            return (
              <div key={section.id}>
                <div className="flex items-center justify-between mb-2 gap-2">
                  <h3 className="text-xs font-medium text-gray-500 uppercase tracking-wide">
                    {section.label}
                  </h3>
                  <div className="flex items-center gap-2">
                    {sectionCards.length > 1 && (
                      <span className="text-xs text-gray-600">
                        {sectionCards.length} cards
                      </span>
                    )}
                    {onRefreshSection && (
                      <button
                        type="button"
                        onClick={async () => {
                          setRefreshingSection(section.id);
                          try {
                            await onRefreshSection(section.id);
                          } finally {
                            setRefreshingSection(null);
                          }
                        }}
                        disabled={refreshingSection !== null}
                        className="p-1.5 rounded-md text-gray-500 hover:text-indigo-400 hover:bg-white/5 disabled:opacity-50 disabled:pointer-events-none transition-colors"
                        title="Refresh this section with new information"
                        aria-label={`Refresh ${section.label}`}
                      >
                        {refreshingSection === section.id ? (
                          <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24" aria-hidden>
                            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                          </svg>
                        ) : (
                          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2} aria-hidden>
                            <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                          </svg>
                        )}
                      </button>
                    )}
                  </div>
                </div>
                <div className="flex flex-col gap-3">
                  {sectionCards.length > 0 ? (
                    sectionCards.map(card => (
                      <InfoCardComponent
                        key={card.id}
                        card={card}
                        onDismiss={() => onDismissCard(card.id)}
                      />
                    ))
                  ) : (
                    <p className="text-gray-500 text-xs py-2">
                      {section.id === 'album' ? 'No album info found for this track.' : 'No song info found for this track.'}
                    </p>
                  )}
                </div>
              </div>
            );
          })}
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
            <p style={{ margin: '4px 0 0 0', fontSize: 14, color: '#6b7280' }}>{track.album || '—'}</p>
            {cards.length > 0 && (
              <p style={{ margin: '10px 0 0 0', fontSize: 13, color: '#6366f1', fontWeight: 500 }}>{cards.length} liner notes</p>
            )}
          </div>
        </div>
        <div style={{ background: '#1a1a1a', padding: '16px 16px 32px 16px' }}>
          {cardsContent}
          {streamDone && cards.length > 0 && cards.length < 4 && (
            <p className="text-gray-500 text-xs mt-4 text-center">Add API keys (Last.fm, Genius, GROQ) in backend .env for more sources.</p>
          )}
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
            <p style={{ margin: '4px 0 0 0', fontSize: 16, color: '#6b7280' }}>{track.album || '—'}</p>
            {cards.length > 0 && (
              <p style={{ margin: '12px 0 0 0', fontSize: 14, color: '#6366f1', fontWeight: 500 }}>{cards.length} liner notes</p>
            )}
          </div>
        </div>
        <div style={{ flex: 1, background: '#1a1a1a', padding: '24px 24px 48px 24px' }}>
          {cardsContent}
          {streamDone && cards.length > 0 && cards.length < 4 && (
            <p className="text-gray-500 text-xs mt-4 text-center">
              Add API keys (Last.fm, Genius, GROQ) in backend .env for more sources.
            </p>
          )}
        </div>
      </div>
      {streamDone && cards.length > 0 && cards.length < 4 && (
        <p className="text-gray-500 text-xs py-4 text-center bg-[#0f0f0f]">
          Add API keys (Last.fm, Genius, GROQ) in backend .env for more sources.
        </p>
      )}
    </div>
  );
}
