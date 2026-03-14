import { useState, type CSSProperties } from 'react';
import type { InfoCard, CardSource } from '../types';
import { parseMarkdownLinks, normalizeMarkdownLinks, renderWithLineBreaks } from '../utils/markdownLinks';

interface InfoCardComponentProps {
  card: InfoCard;
  onDismiss: () => void;
  style?: CSSProperties;
}

export function InfoCardComponent({ card, onDismiss, style }: InfoCardComponentProps) {
  const sourceConfig = getSourceConfig(card.source);
  const [isExpanded, setIsExpanded] = useState(false);
  
  const hasMoreContent = card.full_content && card.full_content.length > card.summary.length;
  const showReadMore = hasMoreContent || card.summary.length > 150;
  const rawContent = isExpanded && card.full_content ? card.full_content : card.summary;
  const displayContent = normalizeMarkdownLinks(rawContent);

  return (
    <div
      className="bg-[#252525] rounded-xl overflow-hidden animate-slide-in card-shadow relative"
      style={style}
    >
      {/* Dismiss button - positioned absolutely */}
      <button
        onClick={onDismiss}
        className="absolute top-2 right-2 w-8 h-8 flex items-center justify-center text-gray-500 hover:text-gray-300 rounded-full hover:bg-white/10 transition-colors z-10"
      >
        <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>

      {/* Card content */}
      <div className="p-4 pr-12">
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
            
            <h4 className="font-medium text-white mb-2">
              {card.title}
            </h4>
            
            <div className={`text-sm text-gray-300 leading-relaxed ${isExpanded ? '' : 'line-clamp-4'}`}>
              {displayContent.split('\n\n').map((paragraph, i) => (
                <p key={i} className={i > 0 ? 'mt-4' : ''}>
                  {renderWithLineBreaks(parseMarkdownLinks(paragraph))}
                </p>
              ))}
            </div>
            
            {/* Expand/Collapse button */}
            {showReadMore && (
              <button
                onClick={() => setIsExpanded(!isExpanded)}
                className="mt-2 text-sm text-indigo-400 hover:text-indigo-300 flex items-center gap-1"
              >
                <span>{isExpanded ? 'Show less' : 'Read more'}</span>
                <svg 
                  className={`w-4 h-4 transition-transform ${isExpanded ? 'rotate-180' : ''}`} 
                  fill="none" 
                  viewBox="0 0 24 24" 
                  stroke="currentColor"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            )}
          </div>
        </div>
        
        {/* Action buttons - only show when expanded */}
        {isExpanded && card.url && (
          <div className="flex items-center gap-2 mt-4 pt-3 border-t border-white/10">
            <a
              href={card.url}
              target="_blank"
              rel="noopener noreferrer"
              className="flex-1 flex items-center justify-center gap-2 py-2 px-4 bg-indigo-600 hover:bg-indigo-500 rounded-lg text-sm font-medium transition-colors"
              onClick={(e) => e.stopPropagation()}
            >
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
              <span>View on {sourceConfig.label}</span>
            </a>
          </div>
        )}
      </div>
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
