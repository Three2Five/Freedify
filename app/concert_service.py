"""
Concert Service - Ticketmaster Discovery API + SeatGeek fallback
Provides upcoming concert search for artists
"""

import os
import httpx
import logging
from typing import List, Dict, Optional, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# API Configuration
TICKETMASTER_API_KEY = os.getenv("TICKETMASTER_API_KEY", "")
SEATGEEK_CLIENT_ID = os.getenv("SEATGEEK_CLIENT_ID", "")

TICKETMASTER_BASE = "https://app.ticketmaster.com/discovery/v2"
SEATGEEK_BASE = "https://api.seatgeek.com/2"


class ConcertService:
    """Service for fetching upcoming concerts from Ticketmaster and SeatGeek."""
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=30.0, follow_redirects=True)
    
    async def search_ticketmaster(
        self, 
        artist: str, 
        city: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search Ticketmaster Discovery API for events.
        
        Args:
            artist: Artist name to search
            city: Optional city to filter by
            limit: Max results to return
            
        Returns:
            List of normalized event objects
        """
        if not TICKETMASTER_API_KEY:
            logger.warning("TICKETMASTER_API_KEY not set")
            return []
        
        try:
            params = {
                "apikey": TICKETMASTER_API_KEY,
                "keyword": artist,
                "classificationName": "music",
                "size": limit,
                "sort": "date,asc"
            }
            
            # Normalize city name (remove "City" suffix, common variants)
            if city:
                normalized_city = city.replace(" City", "").replace(" city", "").strip()
                params["city"] = normalized_city
            
            response = await self.client.get(
                f"{TICKETMASTER_BASE}/events.json",
                params=params
            )
            
            if response.status_code != 200:
                logger.error(f"Ticketmaster API error: {response.status_code}")
                return []
            
            data = response.json()
            events = data.get("_embedded", {}).get("events", [])
            
            logger.info(f"Ticketmaster returned {len(events)} events for '{artist}'")
            
            # If no events found with city filter, try without
            if not events and city:
                logger.info(f"No events with city filter, trying without...")
                del params["city"]
                response = await self.client.get(
                    f"{TICKETMASTER_BASE}/events.json",
                    params=params
                )
                if response.status_code == 200:
                    data = response.json()
                    events = data.get("_embedded", {}).get("events", [])
                    logger.info(f"Ticketmaster (no city) returned {len(events)} events")
            
            return [self._normalize_ticketmaster_event(e) for e in events]
            
        except Exception as e:
            logger.error(f"Ticketmaster search error: {e}")
            return []
    
    def _normalize_ticketmaster_event(self, event: Dict) -> Dict[str, Any]:
        """Convert Ticketmaster event to normalized format."""
        # Get venue info
        venues = event.get("_embedded", {}).get("venues", [])
        venue = venues[0] if venues else {}
        
        # Get date/time
        dates = event.get("dates", {})
        start = dates.get("start", {})
        
        # Get price range
        price_ranges = event.get("priceRanges", [])
        price = price_ranges[0] if price_ranges else {}
        
        # Get image
        images = event.get("images", [])
        image = next((img["url"] for img in images if img.get("ratio") == "16_9"), None)
        if not image and images:
            image = images[0].get("url")
        
        # Get artist name from attractions
        attractions = event.get("_embedded", {}).get("attractions", [])
        artist_name = attractions[0].get("name") if attractions else event.get("name", "")
        
        return {
            "id": event.get("id", ""),
            "name": event.get("name", ""),
            "artist": artist_name,
            "venue": venue.get("name", "Unknown Venue"),
            "city": venue.get("city", {}).get("name", ""),
            "state": venue.get("state", {}).get("stateCode", ""),
            "country": venue.get("country", {}).get("countryCode", ""),
            "date": start.get("localDate", ""),
            "time": start.get("localTime", ""),
            "ticket_url": event.get("url", ""),
            "price_min": price.get("min"),
            "price_max": price.get("max"),
            "currency": price.get("currency", "USD"),
            "image": image,
            "source": "ticketmaster"
        }
    
    async def search_seatgeek(
        self,
        artist: str,
        city: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search SeatGeek API for events (fallback).
        
        Args:
            artist: Artist name to search
            city: Optional city to filter by
            limit: Max results to return
            
        Returns:
            List of normalized event objects
        """
        if not SEATGEEK_CLIENT_ID:
            logger.warning("SEATGEEK_CLIENT_ID not set")
            return []
        
        try:
            # Use performers.slug for better matching (slugify artist name)
            artist_slug = artist.lower().replace(" ", "-").replace("'", "")
            
            params = {
                "client_id": SEATGEEK_CLIENT_ID,
                "performers.slug": artist_slug,
                "per_page": limit,
                "sort": "datetime_utc.asc"
            }
            
            response = await self.client.get(
                f"{SEATGEEK_BASE}/events",
                params=params
            )
            
            if response.status_code != 200:
                logger.error(f"SeatGeek API error: {response.status_code}")
                return []
            
            data = response.json()
            events = data.get("events", [])
            
            logger.info(f"SeatGeek returned {len(events)} events for '{artist}'")
            
            # If no results with slug, try keyword search
            if not events:
                logger.info(f"SeatGeek slug search failed, trying q=")
                params = {
                    "client_id": SEATGEEK_CLIENT_ID,
                    "q": artist,
                    "type": "concert",
                    "per_page": limit,
                    "sort": "datetime_utc.asc"
                }
                response = await self.client.get(
                    f"{SEATGEEK_BASE}/events",
                    params=params
                )
                if response.status_code == 200:
                    data = response.json()
                    events = data.get("events", [])
                    logger.info(f"SeatGeek (q=) returned {len(events)} events")
            
            return [self._normalize_seatgeek_event(e) for e in events]
            
        except Exception as e:
            logger.error(f"SeatGeek search error: {e}")
            return []
    
    def _normalize_seatgeek_event(self, event: Dict) -> Dict[str, Any]:
        """Convert SeatGeek event to normalized format."""
        venue = event.get("venue", {})
        performers = event.get("performers", [])
        performer = performers[0] if performers else {}
        
        # Parse datetime
        datetime_utc = event.get("datetime_utc", "")
        date_str = ""
        time_str = ""
        if datetime_utc:
            try:
                dt = datetime.fromisoformat(datetime_utc.replace("Z", "+00:00"))
                date_str = dt.strftime("%Y-%m-%d")
                time_str = dt.strftime("%H:%M:%S")
            except:
                pass
        
        # Get stats for pricing
        stats = event.get("stats", {})
        
        return {
            "id": str(event.get("id", "")),
            "name": event.get("title", ""),
            "artist": performer.get("name", event.get("title", "")),
            "venue": venue.get("name", "Unknown Venue"),
            "city": venue.get("city", ""),
            "state": venue.get("state", ""),
            "country": venue.get("country", ""),
            "date": date_str,
            "time": time_str,
            "ticket_url": event.get("url", ""),
            "price_min": stats.get("lowest_price"),
            "price_max": stats.get("highest_price"),
            "currency": "USD",
            "image": performer.get("image"),
            "source": "seatgeek"
        }
    
    async def search_events(
        self,
        artist: str,
        city: Optional[str] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search for events with Ticketmaster primary, SeatGeek fallback.
        
        Args:
            artist: Artist name to search
            city: Optional city to filter by
            limit: Max results to return
            
        Returns:
            List of normalized event objects
        """
        # Try Ticketmaster first
        events = await self.search_ticketmaster(artist, city, limit)
        
        # If no results or Ticketmaster unavailable, try SeatGeek
        if not events:
            logger.info(f"Falling back to SeatGeek for: {artist}")
            events = await self.search_seatgeek(artist, city, limit)
        
        return events
    
    async def get_events_for_artists(
        self,
        artists: List[str],
        cities: Optional[List[str]] = None,
        limit_per_artist: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get upcoming events for multiple artists.
        
        Args:
            artists: List of artist names
            cities: Optional list of cities to filter by
            limit_per_artist: Max events per artist
            
        Returns:
            List of all events, sorted by date
        """
        all_events = []
        
        for artist in artists[:10]:  # Limit to 10 artists to avoid rate limits
            if cities:
                # Search each city
                for city in cities[:3]:  # Limit to 3 cities
                    events = await self.search_events(artist, city, limit_per_artist)
                    all_events.extend(events)
            else:
                events = await self.search_events(artist, None, limit_per_artist)
                all_events.extend(events)
        
        # Deduplicate by event ID
        seen_ids = set()
        unique_events = []
        for event in all_events:
            event_id = f"{event['source']}_{event['id']}"
            if event_id not in seen_ids:
                seen_ids.add(event_id)
                unique_events.append(event)
        
        # Sort by date
        unique_events.sort(key=lambda e: e.get("date", "9999-99-99"))
        
        return unique_events
    
    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()


# Singleton instance
concert_service = ConcertService()
