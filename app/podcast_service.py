"""
Podcast service using PodcastIndex API.
https://podcastindex-org.github.io/docs-api/
"""
import httpx
import logging
import hashlib
import time
import base64
import os
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# API Keys - MUST be set via environment variables (never commit real keys!)
PODCASTINDEX_KEY = os.getenv("PODCASTINDEX_KEY", "")
PODCASTINDEX_SECRET = os.getenv("PODCASTINDEX_SECRET", "")

class PodcastService:
    """Service for searching podcasts via PodcastIndex API."""
    
    BASE_URL = "https://api.podcastindex.org/api/1.0"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=15.0)
        self.api_key = PODCASTINDEX_KEY
        self.api_secret = PODCASTINDEX_SECRET

    def _get_auth_headers(self) -> Dict[str, str]:
        """Generate authentication headers for PodcastIndex API."""
        epoch_time = int(time.time())
        data_to_hash = self.api_key + self.api_secret + str(epoch_time)
        sha1_hash = hashlib.sha1(data_to_hash.encode('utf-8')).hexdigest()
        
        return {
            "X-Auth-Key": self.api_key,
            "X-Auth-Date": str(epoch_time),
            "Authorization": sha1_hash,
            "User-Agent": "Freedify/1.0"
        }

    async def search_podcasts(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for podcasts by term."""
        try:
            params = {"q": query, "max": limit}
            response = await self.client.get(
                f"{self.BASE_URL}/search/byterm",
                params=params,
                headers=self._get_auth_headers()
            )
            
            if response.status_code != 200:
                logger.error(f"PodcastIndex search failed: {response.status_code}")
                return []
                
            data = response.json()
            feeds = data.get("feeds", [])
            
            return [self._format_podcast(feed) for feed in feeds[:limit]]
            
        except Exception as e:
            logger.error(f"Podcast search error: {e}")
            return []

    async def get_podcast_episodes(self, feed_id: str, limit: int = 50) -> Optional[Dict[str, Any]]:
        """Get episodes for a podcast by feed ID."""
        try:
            # First get feed info
            feed_response = await self.client.get(
                f"{self.BASE_URL}/podcasts/byfeedid",
                params={"id": feed_id},
                headers=self._get_auth_headers()
            )
            
            if feed_response.status_code != 200:
                logger.error(f"Failed to get feed info: {feed_response.status_code}")
                return None
            
            feed_data = feed_response.json().get("feed", {})
            
            # Get episodes
            episodes_response = await self.client.get(
                f"{self.BASE_URL}/episodes/byfeedid",
                params={"id": feed_id, "max": limit},
                headers=self._get_auth_headers()
            )
            
            if episodes_response.status_code != 200:
                logger.error(f"Failed to get episodes: {episodes_response.status_code}")
                return None
            
            episodes_data = episodes_response.json().get("items", [])
            
            # Format episodes as tracks
            tracks = []
            for ep in episodes_data:
                audio_url = ep.get("enclosureUrl")
                if not audio_url:
                    continue
                
                # Create ID that audio_service can decode (LINK:base64)
                safe_id = f"LINK:{base64.urlsafe_b64encode(audio_url.encode()).decode()}"
                
                duration_s = ep.get("duration", 0)
                duration_str = f"{int(duration_s // 60)}:{int(duration_s % 60):02d}" if duration_s else "0:00"
                
                tracks.append({
                    "id": safe_id,
                    "type": "track",
                    "name": ep.get("title", "Unknown Episode"),
                    "artists": feed_data.get("author") or feed_data.get("title", "Unknown"),
                    "album": feed_data.get("title", "Podcast"),
                    "album_art": ep.get("image") or feed_data.get("image") or "/static/icon.svg",
                    "duration": duration_str,
                    "isrc": safe_id,
                    "source": "podcast"
                })
            
            return {
                "id": f"pod_{feed_id}",
                "type": "album",
                "name": feed_data.get("title", "Unknown Podcast"),
                "artists": feed_data.get("author") or "Podcast",
                "image": feed_data.get("image") or "/static/icon.svg",
                "album_art": feed_data.get("image") or "/static/icon.svg",
                "tracks": tracks,
                "total_tracks": len(tracks),
                "source": "podcast"
            }
            
        except Exception as e:
            logger.error(f"Error fetching episodes for feed {feed_id}: {e}")
            return None

    def _format_podcast(self, feed: dict) -> dict:
        """Format PodcastIndex feed to app format."""
        return {
            "id": f"pod_{feed.get('id')}",
            "type": "album",
            "is_podcast": True,
            "name": feed.get("title", "Unknown Podcast"),
            "artists": feed.get("author") or feed.get("ownerName", "Unknown"),
            "album_art": feed.get("image") or feed.get("artwork") or "/static/icon.svg",
            "description": feed.get("description", "")[:150],
            "source": "podcast"
        }

    async def close(self):
        await self.client.aclose()

podcast_service = PodcastService()
