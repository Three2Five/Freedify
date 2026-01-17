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

# API Keys - MUST be set via environment variables
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
        if not self.api_key or not self.api_secret:
            logger.warning("PodcastIndex API keys are missing!")
            return {}

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
        """Search for podcasts by term. Uses PodcastIndex if configured, else iTunes."""
        # Use iTunes fallback if no PodcastIndex keys
        if not self.api_key or not self.api_secret:
            logger.info("No PodcastIndex keys - using iTunes fallback")
            return await self._search_itunes(query, limit)
        
        try:
            params = {"q": query, "max": limit}
            response = await self.client.get(
                f"{self.BASE_URL}/search/byterm",
                params=params,
                headers=self._get_auth_headers()
            )
            
            if response.status_code != 200:
                logger.error(f"PodcastIndex search failed: {response.status_code}")
                # Fall back to iTunes on error
                return await self._search_itunes(query, limit)
                
            data = response.json()
            feeds = data.get("feeds", [])
            
            return [self._format_podcast(feed) for feed in feeds[:limit]]
            
        except Exception as e:
            logger.error(f"Podcast search error: {e}")
            # Fall back to iTunes on exception
            return await self._search_itunes(query, limit)
    
    async def _search_itunes(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Fallback: Search podcasts via iTunes Search API (no API key needed)."""
        try:
            response = await self.client.get(
                "https://itunes.apple.com/search",
                params={
                    "term": query,
                    "media": "podcast",
                    "limit": limit
                }
            )
            
            if response.status_code != 200:
                logger.error(f"iTunes search failed: {response.status_code}")
                return []
            
            data = response.json()
            results = data.get("results", [])
            
            return [self._format_itunes_podcast(p) for p in results]
            
        except Exception as e:
            logger.error(f"iTunes search error: {e}")
            return []
    
    def _format_itunes_podcast(self, podcast: dict) -> dict:
        """Format iTunes podcast result to app format."""
        # iTunes returns feedUrl which we can use to fetch episodes
        feed_url = podcast.get("feedUrl", "")
        # Create a simple ID from the collection ID
        collection_id = podcast.get("collectionId", 0)
        
        return {
            "id": f"itunes_{collection_id}",
            "type": "album",
            "is_podcast": True,
            "name": podcast.get("collectionName", "Unknown Podcast"),
            "artists": podcast.get("artistName", "Unknown"),
            "album_art": podcast.get("artworkUrl600") or podcast.get("artworkUrl100") or "/static/icon.svg",
            "description": podcast.get("primaryGenreName", ""),
            "source": "podcast",
            "feed_url": feed_url  # Store for episode fetching
        }

    async def get_podcast_episodes(self, feed_id: str, limit: int = 50) -> Optional[Dict[str, Any]]:
        """Get episodes for a podcast by feed ID (supports PodcastIndex and iTunes)."""
        try:
            # Handle iTunes podcasts - need to look up feed URL first
            if feed_id.startswith("itunes_"):
                collection_id = feed_id.replace("itunes_", "")
                return await self._get_itunes_episodes(collection_id, limit)
            
            # Handle PodcastIndex podcasts
            if not self.api_key:
                logger.warning("Cannot fetch PodcastIndex episodes: Missing API Key")
                return None

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
                    "source": "podcast",
                    # Metadata for Info Modal
                    "description": ep.get("description", ""),
                    "datePublished": ep.get("datePublishedPretty", "")
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
    
    async def _get_itunes_episodes(self, collection_id: str, limit: int = 50) -> Optional[Dict[str, Any]]:
        """Fetch episodes for iTunes podcast by looking up feed URL and parsing RSS."""
        import xml.etree.ElementTree as ET
        
        try:
            # Look up podcast to get feed URL
            lookup_response = await self.client.get(
                "https://itunes.apple.com/lookup",
                params={"id": collection_id, "entity": "podcast"}
            )
            
            if lookup_response.status_code != 200:
                logger.error(f"iTunes lookup failed: {lookup_response.status_code}")
                return None
            
            results = lookup_response.json().get("results", [])
            if not results:
                logger.error(f"No iTunes results for collection {collection_id}")
                return None
            
            podcast_info = results[0]
            feed_url = podcast_info.get("feedUrl")
            
            if not feed_url:
                logger.error(f"No feed URL for iTunes podcast {collection_id}")
                return None
            
            # Fetch and parse RSS feed
            feed_response = await self.client.get(feed_url, timeout=30.0)
            if feed_response.status_code != 200:
                logger.error(f"Failed to fetch RSS feed: {feed_response.status_code}")
                return None
            
            # Parse XML
            root = ET.fromstring(feed_response.text)
            channel = root.find("channel")
            if channel is None:
                return None
            
            podcast_title = channel.findtext("title", "Unknown Podcast")
            podcast_author = channel.findtext("{http://www.itunes.com/dtds/podcast-1.0.dtd}author", "Unknown")
            podcast_image = podcast_info.get("artworkUrl600") or podcast_info.get("artworkUrl100") or "/static/icon.svg"
            
            # Parse episodes
            tracks = []
            for idx, item in enumerate(channel.findall("item")):
                if idx >= limit:
                    break
                
                enclosure = item.find("enclosure")
                if enclosure is None:
                    continue
                
                audio_url = enclosure.get("url", "")
                if not audio_url:
                    continue
                
                safe_id = f"LINK:{base64.urlsafe_b64encode(audio_url.encode()).decode()}"
                
                # Parse duration (could be HH:MM:SS or seconds)
                duration_str = "0:00"
                itunes_duration = item.findtext("{http://www.itunes.com/dtds/podcast-1.0.dtd}duration", "")
                if itunes_duration:
                    if ":" in itunes_duration:
                        duration_str = itunes_duration
                    else:
                        try:
                            secs = int(itunes_duration)
                            duration_str = f"{secs // 60}:{secs % 60:02d}"
                        except:
                            pass
                # Get episode image (itunes:image has href attribute)
                episode_image = podcast_image
                itunes_image = item.find("{http://www.itunes.com/dtds/podcast-1.0.dtd}image")
                if itunes_image is not None and itunes_image.get("href"):
                    episode_image = itunes_image.get("href")
                
                tracks.append({
                    "id": safe_id,
                    "type": "track",
                    "name": item.findtext("title", "Unknown Episode"),
                    "artists": podcast_author,
                    "album": podcast_title,
                    "album_art": episode_image,
                    "duration": duration_str,
                    "isrc": safe_id,
                    "source": "podcast",
                    "description": item.findtext("description", ""),
                    "datePublished": item.findtext("pubDate", "")
                })
            
            return {
                "id": f"itunes_{collection_id}",
                "type": "album",
                "name": podcast_title,
                "artists": podcast_author,
                "image": podcast_image,
                "album_art": podcast_image,
                "tracks": tracks,
                "total_tracks": len(tracks),
                "source": "podcast"
            }
            
        except Exception as e:
            logger.error(f"Error fetching iTunes episodes: {e}")
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
