import { useState, useEffect } from 'react';
import { auth } from '../api';
import type { AuthStatus, MusicProvider } from '../types';

interface LoginScreenProps {
  onLogin: (status: AuthStatus) => void;
}

export function LoginScreen({ onLogin }: LoginScreenProps) {
  const [provider, setProvider] = useState<MusicProvider>('spotify');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    
    if (params.get('spotify') === 'connected') {
      window.history.replaceState({}, '', '/');
      auth.getStatus().then((status) => {
        if (status.authenticated) {
          onLogin(status);
        }
      });
    }
    
    const errorParam = params.get('error');
    if (errorParam) {
      window.history.replaceState({}, '', '/');
      const errorMessages: Record<string, string> = {
        'spotify_auth_denied': 'Spotify login was cancelled',
        'spotify_no_code': 'Spotify authentication failed',
        'spotify_auth_failed': 'Could not connect to Spotify',
      };
      setError(errorMessages[errorParam] || 'Authentication failed');
    }
  }, [onLogin]);

  const handleSpotifyLogin = async () => {
    setError(null);
    setIsLoading(true);
    try {
      const forceLogin = sessionStorage.getItem('spotify_force_login') === '1';
      if (forceLogin) sessionStorage.removeItem('spotify_force_login');
      const returnTo = window.location.origin + (window.location.pathname || '/');
      const { url } = await auth.getSpotifyLoginUrl(forceLogin, returnTo);
      // When force_login (after Sign Out), backend returns Spotify logout URL so session is cleared and user must sign in again
      window.location.href = url;
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Could not start Spotify login';
      setError(msg.includes('503') || msg.includes('configured') ? 'Spotify isn’t set up on the server. Add SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET to the backend .env.' : msg);
      setIsLoading(false);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (provider === 'spotify') {
      handleSpotifyLogin();
      return;
    }
    
    setError(null);
    setIsLoading(true);

    try {
      const status = await auth.login(provider, username, password);
      onLogin(status);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Login failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="h-full flex flex-col bg-[#0a0a0a] overflow-auto">
      {/* Background gradient */}
      <div className="absolute inset-0 bg-gradient-to-br from-indigo-500/10 via-transparent to-purple-500/10 pointer-events-none" />
      
      <div className="h-[var(--sat)] flex-shrink-0" />
      
      <div className="flex-1 flex flex-col justify-center items-center px-6 py-8 relative z-10">
        {/* Centered card container */}
        <div className="w-full max-w-sm">
          {/* Logo */}
          <div className="text-center mb-10">
            <div className="w-16 h-16 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-5 shadow-xl shadow-indigo-500/30">
              <svg className="w-8 h-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
              </svg>
            </div>
            <h1 className="text-3xl font-bold mb-2 bg-gradient-to-r from-white to-gray-300 bg-clip-text text-transparent">
              Liner Notes
            </h1>
            <p className="text-gray-500 text-sm">Discover the story behind every song</p>
          </div>

          {/* Main card */}
          <div className="bg-[#141414] rounded-2xl p-6 border border-white/5 shadow-2xl">
            {/* Provider tabs */}
            <div className="flex gap-2 p-1 bg-[#0a0a0a] rounded-xl mb-6">
              <button
                type="button"
                onClick={() => setProvider('spotify')}
                className={`flex-1 py-2.5 rounded-lg font-medium text-sm transition-all flex items-center justify-center gap-2 ${
                  provider === 'spotify'
                    ? 'bg-[#1db954] text-white shadow-lg shadow-[#1db954]/30'
                    : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
                </svg>
                Spotify
              </button>
              <button
                type="button"
                onClick={() => setProvider('tidal')}
                className={`flex-1 py-2.5 rounded-lg font-medium text-sm transition-all ${
                  provider === 'tidal'
                    ? 'bg-white/10 text-white'
                    : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                TIDAL
              </button>
              <button
                type="button"
                onClick={() => setProvider('qobuz')}
                className={`flex-1 py-2.5 rounded-lg font-medium text-sm transition-all ${
                  provider === 'qobuz'
                    ? 'bg-white/10 text-white'
                    : 'text-gray-500 hover:text-gray-300'
                }`}
              >
                Qobuz
              </button>
            </div>

            {/* Login Form */}
            <form onSubmit={handleSubmit}>
              {provider === 'spotify' ? (
                <div className="text-center">
                  <p className="text-gray-400 text-sm mb-5 leading-relaxed">
                    Connect your Spotify account to get liner notes for your music
                  </p>
                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full bg-[#1db954] hover:bg-[#1ed760] text-white font-semibold py-3 px-6 rounded-xl transition-all haptic active:scale-[0.98] shadow-lg shadow-[#1db954]/25 flex items-center justify-center gap-2.5 disabled:opacity-70"
                  >
                    {isLoading ? (
                      <span className="flex items-center gap-2">
                        <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Redirecting to Spotify...
                      </span>
                    ) : (
                      <>
                        <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                          <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
                        </svg>
                        Continue with Spotify
                      </>
                    )}
                  </button>
                  <p className="text-gray-600 text-xs mt-4">
                    You'll be redirected to Spotify to authorize
                  </p>
                </div>
              ) : (
                <div className="space-y-4">
                  <div>
                    <label className="block text-gray-400 text-xs font-medium mb-1.5 ml-1">Email</label>
                    <input
                      type="email"
                      value={username}
                      onChange={(e) => setUsername(e.target.value)}
                      placeholder="your@email.com"
                      required
                      className="w-full bg-[#0a0a0a] border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-gray-400 text-xs font-medium mb-1.5 ml-1">Password</label>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="••••••••"
                      required
                      className="w-full bg-[#0a0a0a] border border-white/10 rounded-xl px-4 py-3 text-white placeholder-gray-600 focus:outline-none focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-500/50 transition-all"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={isLoading}
                    className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-semibold py-3 rounded-xl transition-all disabled:opacity-50 haptic active:scale-[0.98] shadow-lg shadow-indigo-500/25 mt-2"
                  >
                    {isLoading ? (
                      <span className="flex items-center justify-center gap-2">
                        <svg className="w-5 h-5 animate-spin" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                        </svg>
                        Signing in...
                      </span>
                    ) : (
                      'Sign In'
                    )}
                  </button>
                  
                  <p className="text-gray-600 text-xs text-center mt-3">
                    Your credentials are only used to connect to {provider === 'tidal' ? 'TIDAL' : 'Qobuz'}
                  </p>
                </div>
              )}

              {error && (
                <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-red-400 text-sm text-center mt-4">
                  {error}
                </div>
              )}
            </form>
          </div>

          {/* Features */}
          <div className="mt-8 grid grid-cols-3 gap-4 text-center">
            <div>
              <div className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center mx-auto mb-2">
                <svg className="w-5 h-5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <p className="text-gray-500 text-xs">Song stories</p>
            </div>
            <div>
              <div className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center mx-auto mb-2">
                <svg className="w-5 h-5 text-purple-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z" />
                </svg>
              </div>
              <p className="text-gray-500 text-xs">Artist bios</p>
            </div>
            <div>
              <div className="w-10 h-10 bg-white/5 rounded-xl flex items-center justify-center mx-auto mb-2">
                <svg className="w-5 h-5 text-green-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 8h10M7 12h4m1 8l-4-4H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-3l-4 4z" />
                </svg>
              </div>
              <p className="text-gray-500 text-xs">Discussions</p>
            </div>
          </div>
        </div>
      </div>

      <div className="h-[var(--sab)] flex-shrink-0" />
    </div>
  );
}
