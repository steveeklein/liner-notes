export type MusicProvider = 'spotify' | 'tidal' | 'qobuz';

export interface AuthStatus {
  authenticated: boolean;
  provider: MusicProvider | null;
  user_name: string | null;
}

export interface Track {
  id: string;
  title: string;
  artist: string;
  album: string;
  duration: number;
  cover_url: string | null;
  provider: MusicProvider;
}

export interface PlaybackState {
  is_playing: boolean;
  current_track: Track | null;
  position: number;
}

export type CardSource =
  | 'wikipedia'
  | 'musicbrainz'
  | 'discogs'
  | 'allmusic'
  | 'lastfm'
  | 'rateyourmusic'
  | 'albumoftheyear'
  | 'pitchfork'
  | 'genius'
  | 'songmeanings'
  | 'whosampled'
  | 'secondhandsongs'
  | 'setlistfm'
  | 'songkick'
  | 'bandsintown'
  | 'youtube'
  | 'imdb'
  | 'billboard'
  | 'spotify_data'
  | 'reddit'
  | 'web_search'
  | 'llm';

export type CardCategory =
  | 'artist'
  | 'album'
  | 'song'
  | 'genre'
  | 'trivia'
  | 'lyrics'
  | 'samples'
  | 'credits'
  | 'reviews'
  | 'charts'
  | 'concerts'
  | 'videos'
  | 'similar'
  | 'history';

export interface InfoCard {
  id: string;
  source: CardSource;
  title: string;
  summary: string;
  full_content: string | null;
  url: string | null;
  image_url: string | null;
  track_id: string;
  category: CardCategory;
  relevance_score: number;
}

export interface SearchResult {
  tracks: Track[];
  albums: { id: string; name: string }[];
  artists: { id: string; name: string }[];
}
