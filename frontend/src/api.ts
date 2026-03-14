import type {
  AuthStatus,
  MusicProvider,
  PlaybackState,
  SearchResult,
  Track,
  InfoCard,
} from './types';

const API_BASE = '/api';

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const response = await fetch(`${API_BASE}${endpoint}`, {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({}));
    throw new Error(error.detail || `API error: ${response.status}`);
  }

  return response.json();
}

export const auth = {
  login: (provider: MusicProvider, username: string, password: string) =>
    fetchAPI<AuthStatus>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ provider, username, password }),
    }),

  logout: () => fetchAPI<{ status: string }>('/auth/logout', { method: 'POST' }),

  getStatus: () => fetchAPI<AuthStatus>('/auth/status'),

  /** Get Spotify OAuth URL and redirect there (avoids full-page nav proxy issues). */
  getSpotifyLoginUrl: () => fetchAPI<{ url: string }>('/auth/spotify/url'),
};

export const playback = {
  getState: () => fetchAPI<PlaybackState>('/playback/state'),

  play: (trackId: string) =>
    fetchAPI<{ status: string }>(`/playback/play/${trackId}`, { method: 'POST' }),

  pause: () => fetchAPI<{ status: string }>('/playback/pause', { method: 'POST' }),

  resume: () => fetchAPI<{ status: string }>('/playback/resume', { method: 'POST' }),

  next: () => fetchAPI<{ status: string }>('/playback/next', { method: 'POST' }),

  previous: () =>
    fetchAPI<{ status: string }>('/playback/previous', { method: 'POST' }),

  search: (query: string) =>
    fetchAPI<SearchResult>(`/playback/search?query=${encodeURIComponent(query)}`),

  getPlaylists: () => fetchAPI<{ id: string; name: string; track_count: number }[]>('/playback/playlists'),

  getPlaylistTracks: (playlistId: string) =>
    fetchAPI<Track[]>(`/playback/playlist/${playlistId}/tracks`),
};

export const cards = {
  registerTrack: (track: Track) =>
    fetchAPI<{ status: string }>('/cards/register', {
      method: 'POST',
      body: JSON.stringify({
        track_id: track.id,
        artist: track.artist,
        title: track.title,
        album: track.album || '',
      }),
    }),

  getCards: (trackId: string, source?: string) => {
    const params = source ? `?source=${source}` : '';
    return fetchAPI<InfoCard[]>(`/cards/${trackId}${params}`);
  },

  getCardDetail: (trackId: string, cardId: string) =>
    fetchAPI<InfoCard>(`/cards/${trackId}/${cardId}`),

  refresh: (trackId: string) =>
    fetchAPI<{ status: string }>(`/cards/${trackId}/refresh`, { method: 'POST' }),

  connectWebSocket: (
    trackId: string,
    onCard: (card: InfoCard) => void,
    onError?: (error: Event) => void,
    onDone?: (count: number) => void
  ) => {
    const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    const wsHost = window.location.host;
    const wsUrl = `${wsProtocol}//${wsHost}/api/cards/ws/${trackId}`;
    console.log(`[API] Opening WebSocket: ${wsUrl}`);
    const ws = new WebSocket(wsUrl);

    ws.onopen = () => {
      console.log(`[API] WebSocket connected for track: ${trackId}`);
    };

    ws.onclose = (event) => {
      console.log(`[API] WebSocket closed for track: ${trackId}, code: ${event.code}`);
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.error) {
          console.error('[API] Card WebSocket error:', data.error);
        } else if (data.done === true) {
          onDone?.(data.count ?? 0);
        } else {
          onCard(data as InfoCard);
        }
      } catch (e) {
        console.error('[API] Failed to parse card data:', e);
      }
    };

    ws.onerror = (event) => {
      console.error('[API] WebSocket error:', event);
      onError?.(event);
    };

    return ws;
  },
};
