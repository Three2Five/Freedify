"""
Live Show Search Service for Freedify.
Searches Phish.in for Phish shows and Archive.org for other jam bands.
"""
import httpx
import re
from typing import Optional, Dict, List, Any
import logging

logger = logging.getLogger(__name__)


# Bands that have shows on Archive.org Live Music Archive
ARCHIVE_BANDS = {
    "grateful dead": "GratefulDead",
    "dead": "GratefulDead",
    "gd": "GratefulDead",
    "billy strings": "BillyStrings",
    "ween": "Ween",
    "king gizzard": "KingGizzardAndTheLizardWizard",
    "king gizzard & the lizard wizard": "KingGizzardAndTheLizardWizard",
    "king gizzard and the lizard wizard": "KingGizzardAndTheLizardWizard",
    "kglw": "KingGizzardAndTheLizardWizard",
}


class LiveShowService:
    """Service for searching live show archives."""
    
    PHISH_API = "https://phish.in/api/v2"
    ARCHIVE_API = "https://archive.org/advancedsearch.php"
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0)
    
    def detect_live_search(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Detect if a search query is looking for live shows.
        Returns dict with band, year, month if found, else None.
        
        Examples:
        - "Phish 2025" -> {"band": "phish", "year": "2025", "month": None}
        - "Phish 2024/12" -> {"band": "phish", "year": "2024", "month": "12"}
        - "Grateful Dead 1977" -> {"band": "grateful dead", "year": "1977", "month": None}
        """
        query_lower = query.lower().strip()
        
        # Pattern: band name + year or year/month
        # e.g., "Phish 2025", "Grateful Dead 1977/05", "Billy Strings 2023-08"
        pattern = r'^(phish|grateful dead|dead|gd|billy strings|ween|king gizzard.*?|kglw)\s+(\d{4})(?:[/-](\d{1,2}))?$'
        
        match = re.match(pattern, query_lower)
        if match:
            band = match.group(1)
            year = match.group(2)
            month = match.group(3)
            return {
                "band": band,
                "year": year,
                "month": month.zfill(2) if month else None
            }
        return None
    
    async def search_phish_shows(self, year: str, month: str = None) -> List[Dict[str, Any]]:
        """Search Phish.in for shows by year/month."""
        try:
            # Phish.in API endpoint for shows by year
            url = f"{self.PHISH_API}/shows"
            params = {"year": year}
            
            response = await self.client.get(url, params=params)
            if response.status_code != 200:
                logger.warning(f"Phish.in API returned {response.status_code}")
                return []
            
            data = response.json()
            # API v2 returns {'data': [...]} or {'shows': [...]} (observed 'shows' in testing)
            shows = data.get('data', []) or data.get('shows', [])
            
            # Filter by month if specified
            if month:
                shows = [s for s in shows if s.get("date", "").startswith(f"{year}-{month}")]
            
            # Format as albums for the UI
            results = []
            for show in shows[:20]:  # Limit to 20
                date = show.get("date", "")
                venue = show.get("venue", {})
                venue_name = venue.get("name", "") if isinstance(venue, dict) else str(venue)
                location = venue.get("location", "") if isinstance(venue, dict) else ""
                
                results.append({
                    "id": f"phish_{date}",
                    "type": "album",
                    "name": f"Phish - {date}",
                    "artists": "Phish",
                    "album_art": "/static/icon.svg", # phish.in logo 404s, use local icon
                    "release_date": date,
                    "description": f"{venue_name}, {location}" if location else venue_name,
                    "total_tracks": show.get("tracks_count", 0),
                    "source": "phish.in",
                    "import_url": f"https://phish.in/{date}",
                })
            
            return results
        except Exception as e:
            logger.error(f"Phish.in search error: {e}")
            return []
    
    async def search_archive_shows(self, band: str, year: str, month: str = None) -> List[Dict[str, Any]]:
        """Search Archive.org Live Music Archive for shows."""
        try:
            # Get the Archive.org collection name
            band_lower = band.lower()
            collection = None
            for key, val in ARCHIVE_BANDS.items():
                if key in band_lower or band_lower in key:
                    collection = val
                    break
            
            if not collection:
                return []
            
            # Build Archive.org search query
            date_query = f"{year}-{month}" if month else year
            query = f'collection:{collection} AND date:{date_query}* AND mediatype:etree'
            
            params = {
                "q": query,
                "fl[]": ["identifier", "title", "date", "venue", "coverage", "description"],
                "sort[]": "date asc",
                "rows": 20,
                "output": "json",
            }
            
            response = await self.client.get(self.ARCHIVE_API, params=params)
            if response.status_code != 200:
                logger.warning(f"Archive.org API returned {response.status_code}")
                return []
            
            data = response.json()
            docs = data.get("response", {}).get("docs", [])
            
            # Map band collection to display name
            band_names = {
                "GratefulDead": "Grateful Dead",
                "BillyStrings": "Billy Strings",
                "Ween": "Ween",
                "KingGizzardAndTheLizardWizard": "King Gizzard & The Lizard Wizard",
            }
            display_name = band_names.get(collection, collection)
            
            results = []
            for doc in docs:
                identifier = doc.get("identifier", "")
                date = doc.get("date", "")[:10] if doc.get("date") else ""
                title = doc.get("title", f"{display_name} - {date}")
                venue = doc.get("venue", "")
                location = doc.get("coverage", "")
                
                results.append({
                    "id": f"archive_{identifier}",
                    "type": "album",
                    "name": title if title else f"{display_name} - {date}",
                    "artists": display_name,
                    "album_art": f"https://archive.org/services/img/{identifier}",
                    "release_date": date,
                    "description": f"{venue}, {location}" if venue and location else (venue or location or ""),
                    "source": "archive.org",
                    "import_url": f"https://archive.org/details/{identifier}",
                })
            
            return results
        except Exception as e:
            logger.error(f"Archive.org search error: {e}")
            return []
    
    async def search_live_shows(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """
        Main entry point - detect if query is for live shows and search appropriate source.
        Returns None if not a live show query.
        """
        detected = self.detect_live_search(query)
        if not detected:
            return None
        
        band = detected["band"]
        year = detected["year"]
        month = detected["month"]
        
        # Phish -> use phish.in
        if band == "phish":
            logger.info(f"Searching Phish.in for {year}" + (f"/{month}" if month else ""))
            return await self.search_phish_shows(year, month)
        
        # Other bands -> use Archive.org
        logger.info(f"Searching Archive.org for {band} {year}" + (f"/{month}" if month else ""))
        return await self.search_archive_shows(band, year, month)
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
live_show_service = LiveShowService()
