import type { Track } from '../types';

interface MiniPlayerProps {
  track: Track;
  onTap: () => void;
  cardCount: number;
}

export function MiniPlayer({ track, onTap, cardCount }: MiniPlayerProps) {
  return (
    <div className="absolute bottom-[var(--sab)] left-0 right-0 px-3 pb-3">
      <button
        onClick={onTap}
        className="w-full bg-[#252525] rounded-2xl p-3 flex items-center gap-3 card-shadow haptic active:scale-[0.98] transition-transform border border-gray-800"
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
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19V6l12-3v13M9 19c0 1.105-1.343 2-3 2s-3-.895-3-2 1.343-2 3-2 3 .895 3 2z" />
            </svg>
          </div>
        )}

        <div className="flex-1 min-w-0 text-left">
          <p className="font-medium truncate">{track.title}</p>
          <p className="text-sm text-gray-400 truncate">{track.artist}</p>
        </div>

        {cardCount > 0 && (
          <div className="flex items-center gap-1 px-2.5 py-1 bg-indigo-500/20 rounded-full">
            <svg className="w-3.5 h-3.5 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            <span className="text-xs font-medium text-indigo-400">{cardCount}</span>
          </div>
        )}

        <div className="w-10 h-10 bg-indigo-500 rounded-full flex items-center justify-center flex-shrink-0">
          <svg className="w-5 h-5 text-white ml-0.5" fill="currentColor" viewBox="0 0 24 24">
            <path d="M8 5v14l11-7z" />
          </svg>
        </div>
      </button>
    </div>
  );
}
