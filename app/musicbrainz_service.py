"""
MusicBrainz service for Freedify.
Provides metadata enrichment: release year, label, and cover art from Cover Art Archive.
"""
import httpx
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class MusicBrainzService:
    """Service for enriching track metadata from MusicBrainz."""
    
    MB_API = "https://musicbrainz.org/ws/2"
    CAA_API = "https://coverartarchive.org"
    USER_AGENT = "Freedify/1.0 (https://github.com/freedify)"
    
    def __init__(self):
        self.client = httpx.AsyncClient(
            timeout=15.0,
            headers={"User-Agent": self.USER_AGENT}
        )
    
    async def lookup_recording(self, mbid: str) -> Optional[Dict[str, Any]]:
        """Look up a recording by MBID.
        
        Returns:
            {
                'id': '...',
                'name': 'Track Name',
                'artists': 'Artist Name',
                'album': 'Album Name',
                'album_art': '...',
                'release_date': '...',
                'duration': '3:45'
            }
        """
        try:
            response = await self.client.get(
                f"{self.MB_API}/recording/{mbid}",
                params={"fmt": "json", "inc": "releases+artist-credits+release-groups+genres"}
            )
            
            if response.status_code != 200:
                logger.debug(f"MBID lookup failed: {mbid}")
                return None
            
            data = response.json()
            
            # Helper to get artist name
            artist_credit = data.get("artist-credit", [])
            artist_name = ", ".join([ac.get("name", "") for ac in artist_credit]) if artist_credit else "Unknown Artist"
            
            result = {
                "id": mbid,
                "name": data.get("title", "Unknown Track"),
                "artists": artist_name,
                "duration": data.get("length", 0) // 1000 if data.get("length") else 0
            }
            
            # Get release info
            releases = data.get("releases", [])
            if releases:
                release = releases[0]
                result["album"] = release.get("title", "")
                result["release_date"] = release.get("date", "")
                
                # Cover Art
                release_id = release.get("id")
                if release_id:
                    cover_url = await self._get_cover_art(release_id)
                    if cover_url:
                        result["album_art"] = cover_url
            
            return result
            
        except Exception as e:
            logger.error(f"MusicBrainz recording lookup error: {e}")
            return None

    async def lookup_by_isrc(self, isrc: str) -> Optional[Dict[str, Any]]:
        """Look up a recording by ISRC and return enriched metadata.
        
        Returns:
            {
                'release_date': '2020-01-15',
                'label': 'Atlantic Records',
                'cover_art_url': 'https://...',
                'genres': ['pop', 'electronic'],
                'release_id': '...'  # for further lookups
            }
        """
        try:
            # Skip non-standard ISRCs (like dz_ or ytm_ prefixed IDs)
            if not isrc or isrc.startswith(('dz_', 'ytm_', 'LINK:')):
                return None
            
            logger.info(f"Looking up ISRC on MusicBrainz: {isrc}")
            
            # Search for recording by ISRC
            response = await self.client.get(
                f"{self.MB_API}/isrc/{isrc}",
                params={"fmt": "json", "inc": "releases+release-groups+labels+genres"}
            )
            
            if response.status_code != 200:
                logger.debug(f"No MusicBrainz result for ISRC: {isrc}")
                return None
            
            data = response.json()
            recordings = data.get("recordings", [])
            
            if not recordings:
                return None
            
            # Get the first recording's release info
            recording = recordings[0]
            releases = recording.get("releases", [])
            
            if not releases:
                return None
            
            # Use the first release (typically the original)
            release = releases[0]
            release_id = release.get("id", "")
            
            result = {
                "album": release.get("title", ""),
                "release_date": release.get("date", ""),
                "release_id": release_id,
                "label": "",
                "cover_art_url": "",
                "genres": []
            }
            
            # Get label from label-info
            label_info = release.get("label-info", [])
            if label_info and label_info[0].get("label"):
                result["label"] = label_info[0]["label"].get("name", "")
            
            # Get genres from recording
            genres = recording.get("genres", [])
            result["genres"] = [g.get("name", "") for g in genres[:5]]
            
            # Try to get cover art from Cover Art Archive
            # Try to get cover art from Cover Art Archive
            if release_id:
                cover_url = await self._get_cover_art(release_id)
                # Fallback to release group
                if not cover_url:
                     # Access release-group from release object (included via inc=release-groups)
                     rg = release.get("release-group", {})
                     rg_id = rg.get("id")
                     if rg_id:
                         cover_url = await self._get_cover_art(rg_id, entity_type="release-group")
                
                if cover_url:
                    result["cover_art_url"] = cover_url
            
            logger.info(f"MusicBrainz enrichment found: year={result['release_date']}, label={result['label']}")
            return result
            
        except Exception as e:
            logger.debug(f"MusicBrainz lookup error for {isrc}: {e}")
            return None

    async def lookup_by_query(self, title: str, artist: str) -> Optional[Dict[str, Any]]:
        """Look up by query (Title AND Artist) when ISRC is unknown or invalid."""
        if not title or not artist:
            return None
            
        query = f'recording:"{title}" AND artist:"{artist}"'
        logger.info(f"Looking up on MusicBrainz by query: {query}")
        
        try:
            response = await self.client.get(
                f"{self.MB_API}/recording",
                params={
                    "query": query,
                    "limit": 3,
                    "fmt": "json"
                }
            )
            
            if response.status_code != 200:
                logger.warning(f"MB query failed: {response.status_code}")
                return None
                
            data = response.json()
            recordings = data.get("recordings", [])
            
            if not recordings:
                logger.warning(f"MB query returned no recordings for: {title} - {artist}")
                return None
                
            # Use top result
            recording = recordings[0]
            rec_id = recording.get("id")
            
            # Now fetch full details for this recording to get release info consistent with lookup_by_isrc logic
            # OR just reuse what we found if it has releases attached (search usually doesn't include full release details)
            # Better to do a lookup_recording or reuse logic.
            # But the search result typically has 'releases' if we didn't ask for inc? Wait, search result structure is different.
            
            # Let's just return what we can find from the search result or do a secondary lookup
            # Search results usually have a 'releases' list
            releases = recording.get("releases", [])
            if not releases:
                logger.warning(f"MB recording found but has no releases: {title} - {artist}")
                return None
                
            release = releases[0]
            release_date = release.get("date", "")
            
            # Fallback to recording's first-release-date if release date is missing
            if not release_date:
                release_date = recording.get("first-release-date", "")
            
            result = {
                "album": release.get("title", ""),
                "release_date": release_date,
                "release_id": release.get("id", ""),
                "label": "",
                "cover_art_url": "",
                "genres": [tag.get("name") for tag in recording.get("tags", [])[:5]]
            }
            
            # Try to get cover art
            if result["release_id"]:
                # Try specific release first
                cover_url = await self._get_cover_art(result["release_id"])
                
                # Fallback to release group if missing
                if not cover_url:
                    release_group = release.get("release-group", {})
                    rg_id = release_group.get("id")
                    if rg_id:
                        cover_url = await self._get_cover_art(rg_id, entity_type="release-group")

                if cover_url:
                    result["cover_art_url"] = cover_url
                    
            logger.info(f"MusicBrainz query found: {title} -> year={result['release_date']}")
            return result
            
        except Exception as e:
            logger.debug(f"MusicBrainz query error: {e}")
            return None
    
    async def _get_cover_art(self, mbid: str, entity_type: str = "release") -> Optional[str]:
        """Get cover art URL from Cover Art Archive."""
        try:
            response = await self.client.get(
                f"{self.CAA_API}/{entity_type}/{mbid}",
                follow_redirects=True
            )
            
            if response.status_code != 200:
                logger.warning(f"Cover Art Archive not 200 ({response.status_code}) for {entity_type}/{mbid}")
                return None
            
            data = response.json()
            images = data.get("images", [])
            
            # Get front cover, prefer large size
            for img in images:
                if img.get("front"):
                    # Prefer 500px version for quality/speed balance
                    thumbnails = img.get("thumbnails", {})
                    return thumbnails.get("500") or thumbnails.get("large") or img.get("image")
            
            # Fallback to first image
            if images:
                return images[0].get("image")
            
            logger.warning(f"Cover Art Archive response has no images for {entity_type}/{mbid}")
            return None
        except Exception as e:
            logger.warning(f"Cover Art Archive error for {entity_type}/{mbid}: {e}")
            return None
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
musicbrainz_service = MusicBrainzService()
