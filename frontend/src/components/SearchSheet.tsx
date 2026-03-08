import { useState, useCallback, useRef, useEffect } from 'react';
import { playback } from '../api';
import type { Track } from '../types';

interface SearchSheetProps {
  isOpen: boolean;
  onClose: () => void;
  onTrackSelect: (track: Track) => void;
}

export function SearchSheet({ isOpen, onClose, onTrackSelect }: SearchSheetProps) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<Track[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<NodeJS.Timeout>();

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => inputRef.current?.focus(), 100);
    } else {
      setQuery('');
      setResults([]);
    }
  }, [isOpen]);

  const handleSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([]);
      return;
    }

    setIsLoading(true);
    try {
      const data = await playback.search(searchQuery);
      setResults(data.tracks);
    } catch (err) {
      console.error('Search error:', err);
    } finally {
      setIsLoading(false);
    }
  }, []);

  const handleInputChange = useCallback((value: string) => {
    setQuery(value);
    
    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }
    
    debounceRef.current = setTimeout(() => {
      handleSearch(value);
    }, 300);
  }, [handleSearch]);

  const handleTrackClick = useCallback((track: Track) => {
    // Select track to show liner notes
    onTrackSelect(track);
  }, [onTrackSelect]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex flex-col animate-slide-up">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/60 backdrop-blur-sm"
        onClick={onClose}
      />
      
      {/* Sheet */}
      <div className="relative mt-auto bg-[#1a1a1a] rounded-t-3xl max-h-[90vh] flex flex-col">
        <div className="sheet-handle" />
        
        {/* Search Header */}
        <div className="px-4 pb-4">
          <div className="flex items-center gap-3">
            <div className="flex-1 relative">
              <svg 
                className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-500"
                fill="none" 
                viewBox="0 0 24 24" 
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
              <input
                ref={inputRef}
                type="text"
                value={query}
                onChange={(e) => handleInputChange(e.target.value)}
                placeholder="Search songs, artists, albums..."
                className="w-full bg-[#252525] rounded-xl pl-12 pr-4 py-3.5 text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-indigo-500"
              />
              {query && (
                <button
                  onClick={() => {
                    setQuery('');
                    setResults([]);
                    inputRef.current?.focus();
                  }}
                  className="absolute right-3 top-1/2 -translate-y-1/2 w-6 h-6 flex items-center justify-center text-gray-500 hover:text-gray-300"
                >
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              )}
            </div>
            
            <button
              onClick={onClose}
              className="text-indigo-400 font-medium haptic"
            >
              Cancel
            </button>
          </div>
        </div>

        {/* Results */}
        <div className="flex-1 overflow-y-auto hide-scrollbar px-4 pb-8">
          {isLoading ? (
            <div className="py-8 text-center">
              <div className="w-8 h-8 border-2 border-indigo-500 border-t-transparent rounded-full animate-spin mx-auto mb-2" />
              <p className="text-gray-500 text-sm">Searching...</p>
            </div>
          ) : results.length === 0 ? (
            <div className="py-8 text-center">
              {query ? (
                <>
                  <svg className="w-12 h-12 mx-auto mb-3 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                  </svg>
                  <p className="text-gray-500">No results found</p>
                </>
              ) : (
                <>
                  <svg className="w-12 h-12 mx-auto mb-3 text-gray-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                  </svg>
                  <p className="text-gray-500">Search your music library</p>
                </>
              )}
            </div>
          ) : (
            <div className="space-y-1">
              {results.map((track) => (
                <button
                  key={track.id}
                  onClick={() => handleTrackClick(track)}
                  className="w-full flex items-center gap-3 p-3 rounded-xl haptic active:bg-white/5 transition-colors"
                >
                  {track.cover_url ? (
                    <img
                      src={track.cover_url}
                      alt={track.album}
                      className="w-12 h-12 rounded-lg object-cover"
                    />
                  ) : (
                    <div className="w-12 h-12 rounded-lg bg-[#333] flex items-center justify-center">
                      <svg className="w-5 h-5 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13" />
                      </svg>
                    </div>
                  )}
                  
                  <div className="flex-1 text-left min-w-0">
                    <p className="font-medium truncate">{track.title}</p>
                    <p className="text-sm text-gray-400 truncate">
                      {track.artist} • {track.album}
                    </p>
                  </div>

                  <svg className="w-5 h-5 text-indigo-400 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                  </svg>
                </button>
              ))}
            </div>
          )}
        </div>

        {/* Safe area */}
        <div className="h-[var(--sab)]" />
      </div>
    </div>
  );
}
