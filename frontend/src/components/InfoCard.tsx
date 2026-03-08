import type { CSSProperties } from 'react';
import type { InfoCard, CardSource } from '../types';

interface InfoCardComponentProps {
  card: InfoCard;
  onClick: () => void;
  onDismiss: () => void;
  style?: CSSProperties;
}

export function InfoCardComponent({ card, onClick, onDismiss, style }: InfoCardComponentProps) {
  const sourceConfig = getSourceConfig(card.source);

  return (
    <div
      className="bg-[#252525] rounded-xl overflow-hidden animate-slide-in card-shadow"
      style={style}
    >
      <button
        onClick={onClick}
        className="w-full text-left p-4 haptic active:bg-[#2a2a2a] transition-colors"
      >
        <div className="flex items-start gap-3">
          {card.image_url && (
            <img
              src={card.image_url}
              alt=""
              className="w-12 h-12 rounded-lg object-cover flex-shrink-0"
            />
          )}
          
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${sourceConfig.className}`}>
                {sourceConfig.label}
              </span>
            </div>
            
            <h4 className="font-medium text-white mb-1 line-clamp-2">
              {card.title}
            </h4>
            
            <p className="text-sm text-gray-400 line-clamp-3">
              {card.summary}
            </p>
            
            {card.url && (
              <div className="flex items-center gap-1 mt-2 text-xs text-indigo-400">
                <span>Tap to learn more</span>
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 5l7 7-7 7" />
                </svg>
              </div>
            )}
          </div>

          <button
            onClick={(e) => {
              e.stopPropagation();
              onDismiss();
            }}
            className="w-8 h-8 flex items-center justify-center text-gray-500 hover:text-gray-300 rounded-full hover:bg-white/10 transition-colors flex-shrink-0"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>
      </button>
    </div>
  );
}

function getSourceConfig(source: CardSource): { label: string; className: string } {
  const configs: Record<CardSource, { label: string; className: string }> = {
    wikipedia: { label: 'Wikipedia', className: 'source-wikipedia' },
    genius: { label: 'Genius', className: 'source-genius' },
    lastfm: { label: 'Last.fm', className: 'source-lastfm' },
    musicbrainz: { label: 'MusicBrainz', className: 'source-musicbrainz' },
    discogs: { label: 'Discogs', className: 'source-discogs' },
    whosampled: { label: 'WhoSampled', className: 'source-whosampled' },
    billboard: { label: 'Billboard', className: 'source-billboard' },
    youtube: { label: 'YouTube', className: 'source-youtube' },
    reddit: { label: 'Reddit', className: 'source-reddit' },
    spotify_data: { label: 'Spotify', className: 'source-spotify' },
    setlistfm: { label: 'Setlist.fm', className: 'source-setlistfm' },
    allmusic: { label: 'AllMusic', className: 'source-allmusic' },
    llm: { label: 'AI Insight', className: 'source-llm' },
    web_search: { label: 'Web', className: 'source-web' },
    rateyourmusic: { label: 'RYM', className: 'bg-[#1a1a2e] text-white' },
    albumoftheyear: { label: 'AOTY', className: 'bg-[#00b8a9] text-white' },
    pitchfork: { label: 'Pitchfork', className: 'bg-[#ff0000] text-white' },
    songmeanings: { label: 'Meanings', className: 'bg-[#2d5986] text-white' },
    secondhandsongs: { label: 'SHS', className: 'bg-[#4a90d9] text-white' },
    songkick: { label: 'Songkick', className: 'bg-[#f80046] text-white' },
    bandsintown: { label: 'Bandsintown', className: 'bg-[#00cec8] text-black' },
    imdb: { label: 'IMDb', className: 'bg-[#f5c518] text-black' },
  };

  return configs[source] || { label: source, className: 'bg-gray-600 text-white' };
}
