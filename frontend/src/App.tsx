import { useState, useEffect, useCallback, useRef } from 'react';
import { LoginScreen } from './components/LoginScreen';
import { NowPlaying } from './components/NowPlaying';
import { MiniPlayer } from './components/MiniPlayer';
import { SearchSheet } from './components/SearchSheet';
import { auth, playback } from './api';
import type { AuthStatus, Track, InfoCard } from './types';

type Screen = 'home' | 'now-playing' | 'search';

function App() {
  const [authStatus, setAuthStatus] = useState<AuthStatus | null>(null);
  const [currentTrack, setCurrentTrack] = useState<Track | null>(null);
  const [cards, setCards] = useState<InfoCard[]>([]);
  const [activeScreen, setActiveScreen] = useState<Screen>('home');
  const [isSearchOpen, setIsSearchOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isListening, setIsListening] = useState(false);
  const lastTrackIdRef = useRef<string | null>(null);
  const activeScreenRef = useRef<Screen>(activeScreen);
  activeScreenRef.current = activeScreen;

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
            setActiveScreen('now-playing');
          }
          setIsListening(state.is_playing);
        } else {
          lastTrackIdRef.current = null;
          setCurrentTrack(null);
          setCards([]);
          setIsListening(false);
          if (activeScreenRef.current === 'now-playing') setActiveScreen('home');
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
    setActiveScreen('now-playing');
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

      {/* Main Content */}
      <main className="flex-1 overflow-hidden">
        {activeScreen === 'now-playing' && currentTrack ? (
          <NowPlaying
            key={currentTrack.id}
            track={currentTrack}
            cards={cards}
            onNewCard={handleNewCard}
            onDismissCard={handleDismissCard}
            onBack={() => setActiveScreen('home')}
          />
        ) : (
          <div className="h-full flex flex-col">
            {/* Home Screen */}
            <div className="flex-1 overflow-y-auto hide-scrollbar px-4 pb-24">
              <div className="py-6">
                <h2 className="text-2xl font-bold mb-2">
                  {getGreeting()}
                </h2>
                <p className="text-gray-400">
                  {isListening 
                    ? 'Listening to Spotify...'
                    : currentTrack 
                      ? 'Tap the player to see liner notes'
                      : 'Play something in Spotify to get started'
                  }
                </p>
                {isListening && (
                  <div className="flex items-center gap-2 mt-2 text-green-500">
                    <div className="flex gap-0.5">
                      <span className="w-1 h-3 bg-green-500 rounded-full animate-pulse" />
                      <span className="w-1 h-4 bg-green-500 rounded-full animate-pulse" style={{animationDelay: '0.1s'}} />
                      <span className="w-1 h-2 bg-green-500 rounded-full animate-pulse" style={{animationDelay: '0.2s'}} />
                    </div>
                    <span className="text-sm font-medium">Connected to Spotify</span>
                  </div>
                )}
              </div>

              {/* Quick Actions */}
              <div className="grid grid-cols-2 gap-3 mb-6">
                <button
                  onClick={() => setIsSearchOpen(true)}
                  className="bg-[#1a1a1a] rounded-xl p-4 flex items-center gap-3 haptic active:bg-[#252525] transition-colors"
                >
                  <div className="w-10 h-10 bg-indigo-500/20 rounded-full flex items-center justify-center">
                    <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                    </svg>
                  </div>
                  <span className="font-medium">Search</span>
                </button>
                
                <button
                  onClick={() => currentTrack && setActiveScreen('now-playing')}
                  disabled={!currentTrack}
                  className="bg-[#1a1a1a] rounded-xl p-4 flex items-center gap-3 haptic active:bg-[#252525] transition-colors disabled:opacity-50"
                >
                  <div className="w-10 h-10 bg-purple-500/20 rounded-full flex items-center justify-center">
                    <svg className="w-5 h-5 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                  </div>
                  <span className="font-medium">Notes</span>
                </button>
              </div>

              {/* Recent/Now Playing */}
              {currentTrack && (
                <div className="mb-6">
                  <h3 className="text-sm font-medium text-gray-400 mb-3">Now Playing</h3>
                  <button
                    onClick={() => setActiveScreen('now-playing')}
                    className="w-full bg-gradient-to-r from-[#1a1a1a] to-[#252525] rounded-xl p-4 flex items-center gap-4 haptic"
                  >
                    {currentTrack.cover_url ? (
                      <img 
                        src={currentTrack.cover_url} 
                        alt={currentTrack.album}
                        className="w-14 h-14 rounded-lg object-cover"
                      />
                    ) : (
                      <div className="w-14 h-14 rounded-lg bg-[#333] flex items-center justify-center">
                        <svg className="w-6 h-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2z" />
                        </svg>
                      </div>
                    )}
                    <div className="flex-1 text-left">
                      <p className="font-semibold truncate">{currentTrack.title}</p>
                      <p className="text-sm text-gray-400 truncate">{currentTrack.artist}</p>
                    </div>
                    <div className="text-indigo-400">
                      <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                      </svg>
                    </div>
                  </button>
                  
                  {cards.length > 0 && (
                    <p className="text-sm text-gray-500 mt-2 text-center">
                      {cards.length} liner {cards.length === 1 ? 'note' : 'notes'} available
                    </p>
                  )}
                </div>
              )}

              {/* Info Section */}
              <div className="bg-[#1a1a1a] rounded-xl p-4">
                <h3 className="font-medium mb-2">About Liner Notes</h3>
                <p className="text-sm text-gray-400 leading-relaxed">
                  Play a song and discover rich information from Wikipedia, 
                  Genius, AllMusic, Last.fm, and more. Learn about samples, 
                  songwriting credits, chart history, and artist trivia.
                </p>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* Mini Player */}
      {currentTrack && activeScreen === 'home' && (
        <MiniPlayer
          track={currentTrack}
          onTap={() => setActiveScreen('now-playing')}
          cardCount={cards.length}
        />
      )}

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

function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return 'Good morning';
  if (hour < 17) return 'Good afternoon';
  return 'Good evening';
}

export default App;
