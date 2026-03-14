import { useState, useEffect, useCallback, useRef } from 'react';
import { LoginScreen } from './components/LoginScreen';
import { NowPlaying } from './components/NowPlaying';
import { SearchSheet } from './components/SearchSheet';
import { auth, playback, cards as cardsApi } from './api';
import type { AuthStatus, Track, InfoCard } from './types';

function App() {
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [currentTrack, setCurrentTrack] = useState<Track | null>(null);
  const [cards, setCards] = useState<InfoCard[]>([]);
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const lastTrackIdRef = useRef<string | null>(null);

  useEffect(() => {
    auth.getStatus()
      .then(setAuthStatus)
      .catch(() => setAuthStatus({ authenticated: false, provider: null, user_name: null }))
      .finally(() => setIsLoading(false));
  }, []);

  // Poll Spotify for currently playing track
  useEffect(() => {
    if (!authStatus?.authenticated) return;

    let pollInterval: NodeJS.Timeout;
    
    const pollPlayback = async () => {
      try {
        const state = await playback.getState();
        if (!state.current_track && state.is_playing === false) {
          console.log('[Poll] Playback state: no track (play something in Spotify to see it here)');
        }
        if (state.current_track) {
          const isNewTrack = state.current_track.id !== lastTrackIdRef.current;
          if (isNewTrack) {
            lastTrackIdRef.current = state.current_track.id;
            setCurrentTrack(state.current_track);
            setCards([]);
          }
          setIsListening(state.is_playing);
        } else {
          lastTrackIdRef.current = null;
          setCurrentTrack(null);
          setCards([]);
          setIsListening(false);
          // Stay on now-playing; empty state will show "play something"
        }
      } catch (err) {
        console.error('Playback poll error:', err);
        setIsListening(false);
      }
    };

    // Poll every 2 seconds so track changes update quickly
    pollPlayback();
    pollInterval = setInterval(pollPlayback, 2000);

    return () => clearInterval(pollInterval);
  }, [authStatus?.authenticated]);

  const handleLogin = useCallback((status: AuthStatus) => {
    setAuthStatus(status);
  }, []);

  const handleLogout = useCallback(async () => {
    await auth.logout();
    setAuthStatus({ authenticated: false, provider: null, user_name: null });
    setCurrentTrack(null);
    setCards([]);
  }, []);

  const handleTrackSelect = useCallback((track: Track) => {
    setCurrentTrack(track);
    setCards([]);
    setIsSearchOpen(false);
  }, []);

  const handleNewCard = useCallback((card: InfoCard) => {
    setCards((prev) => {
      // For LLM cards, only allow one per category (artist, album, song)
      if (card.source === 'llm') {
        const existsLLM = prev.some(
          (c) => c.source === 'llm' && c.category === card.category
        );
        if (existsLLM) return prev;
      }
      
      // For other sources, deduplicate by source + title
      const exists = prev.some(
        (c) => c.source === card.source && c.title === card.title
      );
      if (exists) return prev;
      return [...prev, card];
    });
  }, []);

  const handleDismissCard = useCallback((cardId: string) => {
    setCards((prev) => prev.filter((c) => c.id !== cardId));
  }, []);

  const handleRefreshSection = useCallback(async (sectionId: string) => {
    if (!currentTrack) return;
    try {
      const newCards = await cardsApi.refreshSection(currentTrack.id, sectionId);
      setCards((prev) => prev.filter((c) => c.section !== sectionId).concat(newCards));
    } catch (err) {
      console.error('[Refresh section]', err);
    }
  }, [currentTrack?.id]);

  if (isLoading) {
    return (
      <div className="h-full flex items-center justify-center bg-[#0f0f0f]">
        <div className="text-center">
          <div className="w-12 h-12 border-4 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400 text-sm">Loading...</p>
        </div>
      </div>
    );
  }

  if (!authStatus?.authenticated) {
    return <LoginScreen onLogin={handleLogin} />;
  }

  return (
    <div className="h-full flex flex-col bg-[#0f0f0f] overflow-hidden">
      {/* Status bar spacer for notched devices */}
      <div className="h-[var(--sat)] bg-[#0f0f0f] flex-shrink-0" />
      
      {/* Header */}
      <header className="flex-shrink-0 px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-8 h-8 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-lg flex items-center justify-center">
            <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
            </svg>
          </div>
          <span className="text-lg font-semibold">Liner Notes</span>
        </div>
        
        <button
          onClick={handleLogout}
          className="text-gray-400 text-sm haptic"
        >
          Sign Out
        </button>
      </header>

      {/* Main Content — always the now-playing view */}
      <main className="flex-1 overflow-hidden">
        {currentTrack ? (
          <NowPlaying
            key={currentTrack.id}
            track={currentTrack}
            cards={cards}
            onNewCard={handleNewCard}
            onDismissCard={handleDismissCard}
            onRefreshSection={handleRefreshSection}
          />
        ) : (
          <div className="h-full flex flex-col overflow-y-auto hide-scrollbar px-4 pb-24">
            <div className="py-8 flex-1 flex flex-col items-center justify-center text-center">
              <div className="w-20 h-20 rounded-2xl bg-[#1a1a1a] flex items-center justify-center mb-6">
                <svg className="w-10 h-10 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2z" />
                </svg>
              </div>
              <h2 className="text-xl font-bold mb-2">Now Playing</h2>
              <p className="text-gray-400 mb-6 max-w-[280px]">
                Play something in Spotify or search for a track to see liner notes here.
              </p>
              <button
                onClick={() => setIsSearchOpen(true)}
                className="px-6 py-3 bg-indigo-600 hover:bg-indigo-500 rounded-xl font-medium haptic transition-colors flex items-center gap-2"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                Search
              </button>
              {isListening && (
                <div className="flex items-center gap-2 mt-6 text-green-500">
                  <div className="flex gap-0.5">
                    <span className="w-1 h-3 bg-green-500 rounded-full animate-pulse" />
                    <span className="w-1 h-4 bg-green-500 rounded-full animate-pulse" style={{ animationDelay: '0.1s' }} />
                    <span className="w-1 h-2 bg-green-500 rounded-full animate-pulse" style={{ animationDelay: '0.2s' }} />
                  </div>
                  <span className="text-sm font-medium">Connected to Spotify</span>
                </div>
              )}
            </div>
          </div>
        )}
      </main>

      {/* Search Sheet */}
      <SearchSheet
        isOpen={isSearchOpen}
        onClose={() => setIsSearchOpen(false)}
        onTrackSelect={handleTrackSelect}
      />

      {/* Bottom safe area */}
      <div className="h-[var(--sab)] bg-[#0f0f0f] flex-shrink-0" />
    </div>
  );
}

export default App;
