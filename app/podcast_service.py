import httpx
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

class PodcastService:
    """Service for searching and fetching podcasts via iTunes API."""
    
    SEARCH_URL = "https://itunes.apple.com/search"
    LOOKUP_URL = "https://itunes.apple.com/lookup"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)

    async def search_podcasts(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search for podcasts."""
        try:
            params = {
                "term": query,
                "media": "podcast",
                "entity": "podcast",
                "limit": limit
            }
            response = await self.client.get(self.SEARCH_URL, params=params)
            if response.status_code != 200:
                return []
                
            data = response.json()
            return [self._format_podcast(item) for item in data.get("results", [])]
        except Exception as e:
            logger.error(f"Podcast search error: {e}")
            return []

    async def get_podcast_episodes(self, collection_id: str, limit: int = 50) -> Dict[str, Any]:
        """Get podcast details and episodes."""
        try:
            # First lookup the podcast metadata
            params = {"id": collection_id, "entity": "podcast"}
            response = await self.client.get(self.LOOKUP_URL, params=params)
            
            if response.status_code != 200 or not response.json().get("results"):
                return None
                
            podcast_data = response.json()["results"][0]
            feed_url = podcast_data.get("feedUrl")
            
            if not feed_url:
                return None

            # Now parse the RSS feed (we'll need a simple XML parser or use a library)
            # Since we can't easily add libraries like feedparser without user action, 
            # we'll try to find an API that converts RSS to JSON or do basic parsing.
            # Actually, iTunes Lookup doesn't return episodes.
            # We can use rss2json.com api for free which is easy. 
            # OR we can do a simple regex parse if the feed is standard.
            # Let's use rss2json for simplicity and reliability.
            
            rss_response = await self.client.get(f"https://api.rss2json.com/v1/api.json?rss_url={feed_url}&api_key=your_api_key_here") 
            # api.rss2json.com has limits on free tier. 
            
            # BETTER APPROACH: Just fetch the XML and do basic parsing with python's xml.etree.ElementTree
            # It's built-in.
            
            feed_response = await self.client.get(feed_url, follow_redirects=True)
            if feed_response.status_code != 200:
                return None
                
            return self._parse_rss(feed_response.text, podcast_data)
            
        except Exception as e:
            logger.error(f"Error fetching episodes for {collection_id}: {e}")
            return None

    def _parse_rss(self, xml_content: str, podcast_data: dict) -> Dict[str, Any]:
        """Parse RSS XML content to extract episodes."""
        # We'll use a robust way to parse XML
        import xml.etree.ElementTree as ET
        from email.utils import parsedate_to_datetime
        
        try:
            root = ET.fromstring(xml_content)
            channel = root.find("channel")
            
            episodes = []
            for item in channel.findall("item")[:50]: # Limit to 50
                title = item.find("title").text if item.find("title") is not None else "Unknown Episode"
                enclosure = item.find("enclosure")
                
                audio_url = None
                if enclosure is not None:
                    audio_url = enclosure.get("url")
                else:
                    # Try media:content
                    media = item.find("{http://search.yahoo.com/mrss/}content")
                    if media is not None:
                        audio_url = media.get("url")
                
                if not audio_url: continue
                
                # Create ID that audio_service can decode (LINK:base64)
                import base64
                safe_id = f"LINK:{base64.urlsafe_b64encode(audio_url.encode()).decode()}"
                
                pub_date = item.find("pubDate").text if item.find("pubDate") is not None else ""
                description = item.find("description").text if item.find("description") is not None else ""
                
                # Cleanup description (remove html tags)
                import re
                clean_desc = re.sub('<[^<]+?>', '', description)[:200] + "..." if description else ""

                episodes.append({
                    "id": safe_id,
                    "type": "track",
                    "name": title,
                    "artists": podcast_data.get("artistName", ""),
                    "album": podcast_data.get("collectionName", ""),
                    "album_art": podcast_data.get("artworkUrl600"),
                    "duration": "0:00", # RSS duration is often messy formatted
                    "preview_url": audio_url, # Full episode
                    "is_direct_url": True,
                    "source": "podcast"
                })
            
            return {
                "id": f"pod_{podcast_data['collectionId']}",
                "type": "album", # Treat as album
                "name": podcast_data.get("collectionName"),
                "artists": podcast_data.get("artistName"),
                "album_art": podcast_data.get("artworkUrl600"),
                "tracks": episodes,
                "source": "podcast"
            }
            
        except Exception as e:
            logger.error(f"RSS Parse error: {e}")
            return None

    def _format_podcast(self, item: dict) -> dict:
        """Format iTunes result to app format."""
        return {
            "id": f"pod_{item.get('collectionId')}",
            "type": "album", # Display as album
            "is_podcast": True,
            "name": item.get("collectionName"),
            "artists": item.get("artistName"),
            "album_art": item.get("artworkUrl600"),
            "source": "podcast"
        }

    async def close(self):
        await self.client.aclose()

podcast_service = PodcastService()
