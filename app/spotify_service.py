"""
Spotify service for Freedify.
Provides playlist/album fetching and URL parsing.
ONLY used when a Spotify URL is pasted - not for search (to avoid rate limits).
"""
import httpx
import re
from typing import Optional, Dict, List, Any, Tuple
import logging
from random import randrange

logger = logging.getLogger(__name__)


def get_random_user_agent():
    return f"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_{randrange(11, 15)}_{randrange(4, 9)}) AppleWebKit/{randrange(530, 537)}.{randrange(30, 37)} (KHTML, like Gecko) Chrome/{randrange(80, 105)}.0.{randrange(3000, 4500)}.{randrange(60, 125)} Safari/{randrange(530, 537)}.{randrange(30, 36)}"


class SpotifyService:
    """Service for fetching metadata from Spotify URLs (not for search)."""
    
    TOKEN_URL = "https://open.spotify.com/get_access_token?reason=transport&productType=web_player"
    API_BASE = "https://api.spotify.com/v1"
    
    # Regex patterns for Spotify URLs
    URL_PATTERNS = {
        'track': re.compile(r'(?:spotify\.com/track/|spotify:track:)([a-zA-Z0-9]+)'),
        'album': re.compile(r'(?:spotify\.com/album/|spotify:album:)([a-zA-Z0-9]+)'),
        'playlist': re.compile(r'(?:spotify\.com/playlist/|spotify:playlist:)([a-zA-Z0-9]+)'),
        'artist': re.compile(r'(?:spotify\.com/artist/|spotify:artist:)([a-zA-Z0-9]+)'),
    }
    
    def __init__(self):
        self.access_token: Optional[str] = None
        self.client = httpx.AsyncClient(timeout=30.0)
    
    async def _get_access_token(self) -> str:
        """Get access token from Spotify web player."""
        if self.access_token:
            return self.access_token
        
        headers = {
            "User-Agent": get_random_user_agent(),
            "Accept": "application/json",
            "Referer": "https://open.spotify.com/",
        }
        
        try:
            response = await self.client.get(self.TOKEN_URL, headers=headers)
            if response.status_code == 200:
                data = response.json()
                self.access_token = data.get("accessToken")
                if self.access_token:
                    logger.info("Got Spotify token via direct method")
                    return self.access_token
        except Exception as e:
            logger.warning(f"Direct token fetch failed: {e}")
        
        # Fallback: Extract from embed page
        try:
            embed_url = "https://open.spotify.com/embed/track/4cOdK2wGLETKBW3PvgPWqT"
            response = await self.client.get(embed_url, headers={"User-Agent": get_random_user_agent()})
            if response.status_code == 200:
                token_match = re.search(r'"accessToken":"([^"]+)"', response.text)
                if token_match:
                    self.access_token = token_match.group(1)
                    logger.info("Got Spotify token via embed page")
                    return self.access_token
        except Exception as e:
            logger.warning(f"Embed token fetch failed: {e}")
        
        raise Exception("Failed to get Spotify access token")
    
    async def _api_request(self, endpoint: str, params: dict = None) -> dict:
        """Make authenticated API request with rate limit handling."""
        import asyncio
        
        max_retries = 3
        retry_delay = 2
        
        for attempt in range(max_retries):
            token = await self._get_access_token()
            headers = {
                "Authorization": f"Bearer {token}",
                "User-Agent": get_random_user_agent(),
                "Accept": "application/json",
            }
            response = await self.client.get(f"{self.API_BASE}{endpoint}", headers=headers, params=params)
            
            if response.status_code == 401:
                logger.warning("Got 401, refreshing Spotify token...")
                self.access_token = None
                continue
            
            if response.status_code == 429:
                retry_after = min(int(response.headers.get("Retry-After", retry_delay)), 10)
                logger.warning(f"Rate limited (429). Waiting {retry_after}s before retry {attempt + 1}/{max_retries}")
                await asyncio.sleep(retry_after)
                retry_delay *= 2
                continue
            
            response.raise_for_status()
            return response.json()
        
        response.raise_for_status()
        return response.json()
    
    def parse_spotify_url(self, url: str) -> Optional[Tuple[str, str]]:
        """Parse Spotify URL and return (type, id) or None."""
        for url_type, pattern in self.URL_PATTERNS.items():
            match = pattern.search(url)
            if match:
                return (url_type, match.group(1))
        return None
    
    def is_spotify_url(self, url: str) -> bool:
        """Check if a URL is a Spotify URL."""
        return 'spotify.com/' in url or 'spotify:' in url
    
    # ========== TRACK METHODS ==========
    
    async def get_track_by_id(self, track_id: str) -> Optional[Dict[str, Any]]:
        """Get a single track by ID."""
        try:
            data = await self._api_request(f"/tracks/{track_id}", {"market": "US"})
            return self._format_track(data)
        except:
            return None
    
    def _format_track(self, item: dict) -> dict:
        """Format track data for frontend."""
        return {
            "id": item["id"],
            "type": "track",
            "name": item["name"],
            "artists": ", ".join(a["name"] for a in item["artists"]),
            "artist_names": [a["name"] for a in item["artists"]],
            "album": item["album"]["name"],
            "album_id": item["album"]["id"],
            "album_art": self._get_best_image(item["album"]["images"]),
            "duration_ms": item["duration_ms"],
            "duration": self._format_duration(item["duration_ms"]),
            "isrc": item.get("external_ids", {}).get("isrc"),
            "source": "spotify",
        }
    
    # ========== ALBUM METHODS ==========
    
    async def get_album(self, album_id: str) -> Optional[Dict[str, Any]]:
        """Get album with all tracks."""
        try:
            data = await self._api_request(f"/albums/{album_id}", {"market": "US"})
            album = self._format_album(data)
            
            tracks = []
            for item in data.get("tracks", {}).get("items", []):
                track = {
                    "id": item["id"],
                    "type": "track",
                    "name": item["name"],
                    "artists": ", ".join(a["name"] for a in item["artists"]),
                    "artist_names": [a["name"] for a in item["artists"]],
                    "album": data["name"],
                    "album_id": album_id,
                    "album_art": album["album_art"],
                    "duration_ms": item["duration_ms"],
                    "duration": self._format_duration(item["duration_ms"]),
                    "isrc": None,
                    "source": "spotify",
                }
                tracks.append(track)
            
            album["tracks"] = tracks
            return album
        except Exception as e:
            logger.error(f"Error fetching Spotify album {album_id}: {e}")
            return None
    
    def _format_album(self, item: dict) -> dict:
        return {
            "id": item["id"],
            "type": "album",
            "name": item["name"],
            "artists": ", ".join(a["name"] for a in item.get("artists", [])),
            "album_art": self._get_best_image(item.get("images", [])),
            "release_date": item.get("release_date", ""),
            "total_tracks": item.get("total_tracks", 0),
            "source": "spotify",
        }
    
    # ========== PLAYLIST METHODS ==========
    
    async def get_playlist(self, playlist_id: str) -> Optional[Dict[str, Any]]:
        """Get playlist with all tracks."""
        try:
            data = await self._api_request(f"/playlists/{playlist_id}", {"market": "US"})
            
            playlist = {
                "id": data["id"],
                "type": "playlist",
                "name": data["name"],
                "description": data.get("description", ""),
                "album_art": self._get_best_image(data.get("images", [])),
                "owner": data.get("owner", {}).get("display_name", ""),
                "total_tracks": data.get("tracks", {}).get("total", 0),
                "source": "spotify",
            }
            
            tracks = []
            for item in data.get("tracks", {}).get("items", []):
                track_data = item.get("track")
                if track_data and track_data.get("id"):
                    tracks.append(self._format_track(track_data))
            
            playlist["tracks"] = tracks
            return playlist
        except Exception as e:
            logger.error(f"Error fetching Spotify playlist {playlist_id}: {e}")
            return None
    
    # ========== ARTIST METHODS ==========
    
    async def get_artist(self, artist_id: str) -> Optional[Dict[str, Any]]:
        """Get artist info with top tracks."""
        try:
            artist_data = await self._api_request(f"/artists/{artist_id}")
            artist = {
                "id": artist_data["id"],
                "type": "artist",
                "name": artist_data["name"],
                "image": self._get_best_image(artist_data.get("images", [])),
                "genres": artist_data.get("genres", []),
                "followers": artist_data.get("followers", {}).get("total", 0),
                "source": "spotify",
            }
            
            top_tracks = await self._api_request(f"/artists/{artist_id}/top-tracks", {"market": "US"})
            artist["tracks"] = [self._format_track(t) for t in top_tracks.get("tracks", [])]
            
            return artist
        except Exception as e:
            logger.error(f"Error fetching Spotify artist {artist_id}: {e}")
            return None
    
    # ========== UTILITIES ==========
    
    def _get_best_image(self, images: List[Dict]) -> Optional[str]:
        if not images:
            return None
        sorted_images = sorted(images, key=lambda x: x.get("width", 0), reverse=True)
        return sorted_images[0]["url"] if sorted_images else None
    
    def _format_duration(self, ms: int) -> str:
        seconds = ms // 1000
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"
    
    async def close(self):
        await self.client.aclose()


# Singleton instance
spotify_service = SpotifyService()
