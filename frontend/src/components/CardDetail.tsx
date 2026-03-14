import type { InfoCard, CardSource } from '../types';
import { parseMarkdownLinks, normalizeMarkdownLinks, renderWithLineBreaks } from '../utils/markdownLinks';

interface CardDetailProps {
  card: InfoCard;
  onClose: () => void;
}

export function CardDetail({ card, onClose }: CardDetailProps) {
  const sourceConfig = getSourceConfig(card.source);

  const handleOpenUrl = () => {
    if (card.url) {
      window.open(card.url, '_blank', 'noopener,noreferrer');
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex flex-col animate-fade-in">
      {/* Backdrop */}
      <div 
        className="absolute inset-0 bg-black/80 backdrop-blur-md"
        onClick={onClose}
      />
      
      {/* Modal */}
      <div className="relative mt-auto bg-[#1a1a1a] rounded-t-3xl max-h-[85vh] flex flex-col animate-slide-up">
        <div className="sheet-handle" />
        
        {/* Header */}
        <div className="flex items-center justify-between px-4 py-2">
          <span className={`text-xs px-2.5 py-1 rounded-full font-medium ${sourceConfig.className}`}>
            {sourceConfig.label}
          </span>
          
          <button
            onClick={onClose}
            className="w-8 h-8 flex items-center justify-center text-gray-400 hover:text-white rounded-full hover:bg-white/10 transition-colors"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-y-auto hide-scrollbar px-4 pb-4">
          {card.image_url && (
            <img
              src={card.image_url}
              alt=""
              className="w-full aspect-video rounded-xl object-cover mb-4"
            />
          )}
          
          <h2 className="text-xl font-bold mb-3">{card.title}</h2>
          
          <div className="text-gray-300 leading-relaxed whitespace-pre-wrap">
            {renderWithLineBreaks(parseMarkdownLinks(normalizeMarkdownLinks(card.full_content || card.summary)))}
          </div>
        </div>

        {/* Action Button */}
        {card.url && (
          <div className="px-4 py-4 border-t border-gray-800">
            <button
              onClick={handleOpenUrl}
              className="w-full bg-gradient-to-r from-indigo-500 to-purple-600 text-white font-semibold py-3.5 rounded-xl haptic active:scale-[0.98] transition-transform flex items-center justify-center gap-2"
            >
              <span>View on {sourceConfig.label}</span>
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </button>
          </div>
        )}

        {/* Safe area */}
        <div className="h-[var(--sab)]" />
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
    discussion_search: { label: 'Discussion', className: 'source-discussion' },
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
