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

  const handleSpotifyLogin = () => {
    window.location.href = '/api/auth/spotify/login';
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
    <div className="h-full flex flex-col bg-[#0f0f0f] overflow-auto">
      <div className="h-[var(--sat)] flex-shrink-0" />
      
      <div className="flex-1 flex flex-col justify-center px-6 py-8">
        {/* Logo */}
        <div className="text-center mb-8">
          <div className="w-20 h-20 bg-gradient-to-br from-indigo-500 to-purple-600 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg shadow-indigo-500/20">
            <svg className="w-10 h-10 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zm12-3c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2zM9 10l12-3" />
            </svg>
          </div>
          <h1 className="text-2xl font-bold mb-1">Liner Notes</h1>
          <p className="text-gray-400 text-sm">Discover the story behind every song</p>
        </div>

        {/* Provider Selection */}
        <div className="mb-6">
          <div className="grid grid-cols-3 gap-1 p-1 bg-[#1a1a1a] rounded-xl">
            <button
              type="button"
              onClick={() => setProvider('spotify')}
              className={`py-3 rounded-lg font-medium transition-all flex items-center justify-center gap-1.5 ${
                provider === 'spotify'
                  ? 'bg-[#1db954] text-white'
                  : 'text-gray-400'
              }`}
            >
              <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
              </svg>
              <span className="text-sm">Spotify</span>
            </button>
            <button
              type="button"
              onClick={() => setProvider('tidal')}
              className={`py-3 rounded-lg font-medium transition-all text-sm ${
                provider === 'tidal'
                  ? 'bg-[#252525] text-white'
                  : 'text-gray-400'
              }`}
            >
              TIDAL
            </button>
            <button
              type="button"
              onClick={() => setProvider('qobuz')}
              className={`py-3 rounded-lg font-medium transition-all text-sm ${
                provider === 'qobuz'
                  ? 'bg-[#252525] text-white'
                  : 'text-gray-400'
              }`}
            >
              Qobuz
            </button>
          </div>
        </div>

        {/* Login Form */}
        <form onSubmit={handleSubmit} className="space-y-4">
          {provider === 'spotify' ? (
            <div className="text-center py-4">
              <p className="text-gray-400 text-sm mb-6">
                Connect with your Spotify account to search and play your music
              </p>
              <button
                type="submit"
                className="w-full bg-[#1db954] hover:bg-[#1ed760] text-white font-semibold py-3.5 rounded-xl transition-all haptic active:scale-[0.98] shadow-lg shadow-[#1db954]/20 flex items-center justify-center gap-2"
              >
                <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                  <path d="M12 0C5.4 0 0 5.4 0 12s5.4 12 12 12 12-5.4 12-12S18.66 0 12 0zm5.521 17.34c-.24.359-.66.48-1.021.24-2.82-1.74-6.36-2.101-10.561-1.141-.418.122-.779-.179-.899-.539-.12-.421.18-.78.54-.9 4.56-1.021 8.52-.6 11.64 1.32.42.18.479.659.301 1.02zm1.44-3.3c-.301.42-.841.6-1.262.3-3.239-1.98-8.159-2.58-11.939-1.38-.479.12-1.02-.12-1.14-.6-.12-.48.12-1.021.6-1.141C9.6 9.9 15 10.561 18.72 12.84c.361.181.54.78.241 1.2zm.12-3.36C15.24 8.4 8.82 8.16 5.16 9.301c-.6.179-1.2-.181-1.38-.721-.18-.601.18-1.2.72-1.381 4.26-1.26 11.28-1.02 15.721 1.621.539.3.719 1.02.419 1.56-.299.421-1.02.599-1.559.3z"/>
                </svg>
                Continue with Spotify
              </button>
            </div>
          ) : (
            <>
              <div>
                <input
                  type="email"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  placeholder="Email"
                  required
                  className="w-full bg-[#1a1a1a] border border-gray-800 rounded-xl px-4 py-3.5 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                />
              </div>
              
              <div>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Password"
                  required
                  className="w-full bg-[#1a1a1a] border border-gray-800 rounded-xl px-4 py-3.5 text-white placeholder-gray-500 focus:outline-none focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500 transition-colors"
                />
              </div>

              <button
                type="submit"
                disabled={isLoading}
                className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-semibold py-3.5 rounded-xl transition-all disabled:opacity-50 haptic active:scale-[0.98] shadow-lg shadow-indigo-500/20"
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
            </>
          )}

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 rounded-xl px-4 py-3 text-red-400 text-sm text-center">
              {error}
            </div>
          )}
        </form>

        {/* Footer */}
        <p className="text-center text-gray-500 text-xs mt-8">
          {provider === 'spotify' 
            ? 'You will be redirected to Spotify to authorize'
            : `Your credentials are only used to connect to ${provider === 'tidal' ? 'TIDAL' : 'Qobuz'}`
          }
        </p>
      </div>

      <div className="h-[var(--sab)] flex-shrink-0" />
    </div>
  );
}
