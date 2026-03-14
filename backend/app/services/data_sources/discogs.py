from typing import List, Optional
import re
import uuid
import httpx

from app.models import InfoCard, CardSource
from app.utils.wiki_links import artist_link_markdown
from .base import DataSource


def _discogs_profile_to_markdown(profile: str) -> str:
    """Convert Discogs profile link markup [l=url], [a=id name] to markdown; keep existing links, no Wikipedia added here."""
    if not profile:
        return profile

    def replace_l(m: re.Match) -> str:
        inner = m.group(1).strip()
        parts = inner.split(None, 1)
        url = parts[0]
        label = parts[1] if len(parts) > 1 else url
        return f"[{label}]({url})"

    def replace_a(m: re.Match) -> str:
        inner = m.group(1).strip()
        parts = inner.split(None, 1)
        aid = parts[0]
        name = parts[1] if len(parts) > 1 else "Link"
        return f"[{name}](https://www.discogs.com/artist/{aid})"

    out = re.sub(r"\[l=([^\]]+)\]", replace_l, profile)
    out = re.sub(r"\[a=([^\]]+)\]", replace_a, out)
    return out


class DiscogsSource(DataSource):
    """Fetches release info and credits from Discogs public API."""
    
    BASE_URL = "https://api.discogs.com"
    
    def __init__(self):
        self.headers = {
            "User-Agent": "LinerNotes/1.0"
        }
    
    async def _search_release(self, artist: str, title: str) -> dict | None:
        """Search for a release on Discogs."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/database/search",
                    params={
                        "q": f"{artist} {title}",
                        "type": "release",
                        "per_page": 5
                    },
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    if results:
                        return results[0]
        except Exception as e:
            print(f"Discogs search error: {e}", flush=True)
        return None
    
    async def _search_artist(self, artist: str) -> dict | None:
        """Search for an artist on Discogs."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/database/search",
                    params={
                        "q": artist,
                        "type": "artist",
                        "per_page": 1
                    },
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    results = data.get("results", [])
                    if results:
                        return results[0]
        except Exception as e:
            print(f"Discogs artist search error: {e}", flush=True)
        return None
    
    async def _get_release_details(self, release_id: int) -> dict | None:
        """Get detailed release info."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/releases/{release_id}",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"Discogs release details error: {e}", flush=True)
        return None
    
    async def _get_artist_details(self, artist_id: int) -> dict | None:
        """Get detailed artist info including profile and releases."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/artists/{artist_id}",
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return response.json()
        except Exception as e:
            print(f"Discogs artist details error: {e}", flush=True)
        return None
    
    async def _get_artist_releases(self, artist_id: int) -> list | None:
        """Get artist's releases/albums."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.BASE_URL}/artists/{artist_id}/releases",
                    params={"sort": "year", "sort_order": "desc", "per_page": 10},
                    headers=self.headers,
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return data.get("releases", [])
        except Exception as e:
            print(f"Discogs artist releases error: {e}", flush=True)
        return None
    
    def _build_personnel_card(
        self,
        release_id: int,
        artists: list,
        extraartists: list,
        genre: list,
        style: list,
        track_id: str,
    ) -> Optional[InfoCard]:
        """Build a 'Who's playing on this album' card from Discogs artists + extraartists."""
        lines = []
        seen = set()
        def _name(entry):
            n = entry.get("name")
            if n:
                return n
            art = entry.get("artist")
            return art.get("name") if isinstance(art, dict) else None

        def _artist_url(entry) -> str | None:
            aid = entry.get("id")
            if aid is not None:
                return f"https://www.discogs.com/artist/{aid}"
            art = entry.get("artist")
            if isinstance(art, dict) and art.get("id") is not None:
                return f"https://www.discogs.com/artist/{art['id']}"
            return None

        for a in artists or []:
            name = _name(a)
            if name and name not in seen:
                seen.add(name)
                role = (a.get("role") or "").strip()
                link = artist_link_markdown(name, prefer_url=_artist_url(a))
                lines.append(f"• {link} — {role}" if role else f"• {link}")
        for a in extraartists or []:
            name = _name(a)
            if name and name not in seen:
                seen.add(name)
                role = (a.get("role") or "").strip()
                link = artist_link_markdown(name, prefer_url=_artist_url(a))
                lines.append(f"• {link} — {role}" if role else f"• {link}")
        if not lines:
            return None
        genres = (genre or []) + (style or [])
        is_jazz = any("jazz" in (g or "").lower() for g in genres)
        card_title = "Who's Playing on This Album" if is_jazz else "Album Personnel"
        summary = "\n".join(lines[:25])
        if len(lines) > 25:
            summary += f"\n… and {len(lines) - 25} more"
        return InfoCard(
            id=str(uuid.uuid4()),
            source=CardSource.DISCOGS,
            title=card_title,
            summary=summary,
            url=f"https://www.discogs.com/release/{release_id}",
            track_id=track_id,
            category="credits",
            section="album",
        )

    async def fetch(
        self,
        artist: str,
        track_title: str,
        album: str,
        track_id: str
    ) -> List[InfoCard]:
        cards = []
        
        # Search for the release (prefer album for personnel match when available)
        release = await self._search_release(artist, album or track_title)
        if not release and album:
            release = await self._search_release(artist, track_title)
        if release:
            release_id = release.get("id")
            # Fetch full release details for personnel (artists + extraartists)
            details = await self._get_release_details(release_id) if release_id else None
            if details:
                release = details
            release_url = f"https://www.discogs.com/release/{release_id or ''}"
            
            # Album personnel / who's playing (especially for jazz)
            artists = release.get("artists") or []
            extraartists = release.get("extraartists") or []
            if not isinstance(artists, list):
                artists = [artists] if artists else []
            if not isinstance(extraartists, list):
                extraartists = [extraartists] if extraartists else []
            genres = release.get("genre", [])
            styles = release.get("style", [])
            if not isinstance(genres, list):
                genres = [genres] if genres else []
            if not isinstance(styles, list):
                styles = [styles] if styles else []
            personnel = self._build_personnel_card(
                release_id=release_id or 0,
                artists=artists,
                extraartists=extraartists,
                genre=genres,
                style=styles,
                track_id=track_id,
            )
            if personnel:
                cards.append(personnel)
            
            # Basic release info card
            title_text = release.get("title", "")
            year = release.get("year", "")
            label = release.get("label", ["Unknown label"])[0] if release.get("label") else ""
            format_info = release.get("format", [""])[0] if release.get("format") else ""
            
            summary_parts = []
            if year:
                summary_parts.append(f"Released: {year}")
            if label:
                summary_parts.append(f"Label: {label}")
            if format_info:
                summary_parts.append(f"Format: {format_info}")
            
            if summary_parts:
                cards.append(InfoCard(
                    id=str(uuid.uuid4()),
                    source=CardSource.DISCOGS,
                    title="Release Information",
                    summary=" • ".join(summary_parts),
                    url=release_url,
                    track_id=track_id,
                    category="credits"
                ))
            
            # Get genres/styles
            genres = release.get("genre", [])
            styles = release.get("style", [])
            
            if genres or styles:
                genre_text = ""
                if genres:
                    genre_text += f"Genre: {', '.join(genres[:3])}"
                if styles:
                    if genre_text:
                        genre_text += " | "
                    genre_text += f"Style: {', '.join(styles[:4])}"
                
                cards.append(InfoCard(
                    id=str(uuid.uuid4()),
                    source=CardSource.DISCOGS,
                    title="Genre Classification",
                    summary=genre_text,
                    url=release_url,
                    track_id=track_id,
                    category="genre"
                ))
        
        # Search for artist info  
        artist_result = await self._search_artist(artist)
        if artist_result and artist_result.get("id"):
            artist_id = artist_result["id"]
            artist_url = f"https://www.discogs.com/artist/{artist_id}"
            
            # Get actual artist details
            artist_details = await self._get_artist_details(artist_id)
            
            if artist_details:
                profile = artist_details.get("profile", "")
                
                # Only create card if we have actual profile content
                if profile and len(profile) > 50:
                    # Convert Discogs link markup to markdown so existing links are kept (no Wikipedia added)
                    profile_clean = _discogs_profile_to_markdown(profile)

                    summary = profile_clean[:400]
                    if len(profile_clean) > 400:
                        summary += "..."
                    
                    cards.append(InfoCard(
                        id=str(uuid.uuid4()),
                        source=CardSource.DISCOGS,
                        title=f"About {artist}",
                        summary=summary,
                        full_content=profile_clean if len(profile_clean) > 400 else None,
                        url=artist_url,
                        track_id=track_id,
                        category="artist"
                    ))
            
            # Get artist's top releases
            releases = await self._get_artist_releases(artist_id)
            
            if releases:
                # Filter to main releases (albums)
                albums = [r for r in releases if r.get("type") == "master" or r.get("role") == "Main"][:6]
                
                if albums:
                    album_list = []
                    for alb in albums:
                        title = alb.get("title", "")
                        year = alb.get("year")
                        if title:
                            if year:
                                album_list.append(f"{title} ({year})")
                            else:
                                album_list.append(title)
                    
                    if album_list:
                        cards.append(InfoCard(
                            id=str(uuid.uuid4()),
                            source=CardSource.DISCOGS,
                            title="Discography Highlights",
                            summary="Notable releases:\n\n" + "\n".join(f"• {a}" for a in album_list),
                            url=artist_url,
                            track_id=track_id,
                            category="artist"
                        ))
        
        return cards
