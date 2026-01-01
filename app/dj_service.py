"""
DJ Service for Freedify.
AI-powered setlist generation using Gemini 2.0 Flash.
"""
import os
import logging
from typing import List, Dict, Any, Optional

logger = logging.getLogger(__name__)

# Camelot wheel compatibility chart
# Compatible keys: same key, +1/-1 on wheel, switch A/B (relative major/minor)
CAMELOT_COMPAT = {
    "1A": ["1A", "1B", "12A", "2A"],
    "1B": ["1B", "1A", "12B", "2B"],
    "2A": ["2A", "2B", "1A", "3A"],
    "2B": ["2B", "2A", "1B", "3B"],
    "3A": ["3A", "3B", "2A", "4A"],
    "3B": ["3B", "3A", "2B", "4B"],
    "4A": ["4A", "4B", "3A", "5A"],
    "4B": ["4B", "4A", "3B", "5B"],
    "5A": ["5A", "5B", "4A", "6A"],
    "5B": ["5B", "5A", "4B", "6B"],
    "6A": ["6A", "6B", "5A", "7A"],
    "6B": ["6B", "6A", "5B", "7B"],
    "7A": ["7A", "7B", "6A", "8A"],
    "7B": ["7B", "7A", "6B", "8B"],
    "8A": ["8A", "8B", "7A", "9A"],
    "8B": ["8B", "8A", "7B", "9B"],
    "9A": ["9A", "9B", "8A", "10A"],
    "9B": ["9B", "9A", "8B", "10B"],
    "10A": ["10A", "10B", "9A", "11A"],
    "10B": ["10B", "10A", "9B", "11B"],
    "11A": ["11A", "11B", "10A", "12A"],
    "11B": ["11B", "11A", "10B", "12B"],
    "12A": ["12A", "12B", "11A", "1A"],
    "12B": ["12B", "12A", "11B", "1B"],
}


class DJService:
    """AI-powered DJ setlist generator using Gemini 2.0 Flash."""
    
    def __init__(self):
        self.api_key = os.environ.get("GEMINI_API_KEY")
        self._genai = None
        self._model = None
    
    def _init_genai(self):
        """Lazy initialization of Gemini client."""
        if self._genai is None:
            try:
                import google.generativeai as genai
                if not self.api_key:
                    logger.warning("GEMINI_API_KEY not set - AI features will use rule-based fallback")
                    return False
                genai.configure(api_key=self.api_key)
                self._genai = genai
                self._model = genai.GenerativeModel('gemini-2.0-flash')
                logger.info("Gemini 2.0 Flash initialized successfully")
                return True
            except ImportError:
                logger.warning("google-generativeai not installed - using rule-based fallback")
                return False
            except Exception as e:
                logger.error(f"Failed to initialize Gemini: {e}")
                return False
        return True
    
    def is_harmonically_compatible(self, camelot1: str, camelot2: str) -> bool:
        """Check if two Camelot keys are harmonically compatible."""
        if camelot1 == "?" or camelot2 == "?":
            return False
        return camelot2 in CAMELOT_COMPAT.get(camelot1, [])
    
    def _rule_based_setlist(self, tracks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Generate setlist using rule-based algorithm when AI is unavailable.
        Strategy: Sort by energy, then optimize for harmonic compatibility.
        """
        if len(tracks) <= 2:
            return sorted(tracks, key=lambda t: t.get("energy", 0.5))
        
        # Start with lowest energy track
        sorted_tracks = sorted(tracks, key=lambda t: t.get("energy", 0.5))
        setlist = [sorted_tracks.pop(0)]
        
        while sorted_tracks:
            last = setlist[-1]
            last_camelot = last.get("camelot", "?")
            last_bpm = last.get("bpm", 120)
            
            # Score remaining tracks by compatibility
            def score_track(t):
                score = 0
                # Harmonic compatibility (+10 points)
                if self.is_harmonically_compatible(last_camelot, t.get("camelot", "?")):
                    score += 10
                # BPM proximity (+5 for within 5 BPM, +3 for within 10)
                bpm_diff = abs(t.get("bpm", 120) - last_bpm)
                if bpm_diff <= 5:
                    score += 5
                elif bpm_diff <= 10:
                    score += 3
                # Slight energy increase preferred (+2)
                energy_diff = t.get("energy", 0.5) - last.get("energy", 0.5)
                if 0 < energy_diff < 0.15:
                    score += 2
                return score
            
            # Pick best scoring track
            sorted_tracks.sort(key=score_track, reverse=True)
            setlist.append(sorted_tracks.pop(0))
        
        return setlist
    
    async def generate_setlist(
        self,
        tracks: List[Dict[str, Any]],
        style: str = "progressive"  # or "peak-time", "chill", "journey"
    ) -> Dict[str, Any]:
        """
        Generate an AI-optimized DJ setlist.
        
        Args:
            tracks: List of tracks with bpm, camelot, energy, name, artists
            style: Setlist style preference
            
        Returns:
            Dict with ordered track IDs and mixing suggestions
        """
        if len(tracks) < 2:
            return {
                "ordered_ids": [t.get("id") for t in tracks],
                "suggestions": [],
                "method": "passthrough"
            }
        
        # Try AI generation first
        if self._init_genai() and self._model:
            try:
                result = await self._ai_generate_setlist(tracks, style)
                if result:
                    return result
            except Exception as e:
                logger.error(f"AI setlist generation failed: {e}")
        
        # Fallback to rule-based
        logger.info("Using rule-based setlist generation")
        ordered = self._rule_based_setlist(tracks.copy())
        
        # Generate basic suggestions
        suggestions = []
        for i in range(len(ordered) - 1):
            t1, t2 = ordered[i], ordered[i+1]
            bpm_diff = abs(t2.get("bpm", 0) - t1.get("bpm", 0))
            compatible = self.is_harmonically_compatible(
                t1.get("camelot", "?"), t2.get("camelot", "?")
            )
            
            suggestion = {
                "from_id": t1.get("id"),
                "to_id": t2.get("id"),
                "harmonic_match": compatible,
                "bpm_diff": bpm_diff,
            }
            
            if compatible and bpm_diff <= 5:
                suggestion["tip"] = "Perfect mix - smooth harmonic transition"
            elif compatible:
                suggestion["tip"] = f"Harmonically compatible, adjust BPM by {bpm_diff}"
            elif bpm_diff <= 3:
                suggestion["tip"] = "BPM locked, consider EQ mixing"
            else:
                suggestion["tip"] = "Energy transition - use effects or beat drop"
            
            suggestions.append(suggestion)
        
        return {
            "ordered_ids": [t.get("id") for t in ordered],
            "suggestions": suggestions,
            "method": "rule-based"
        }
    
    async def _ai_generate_setlist(
        self,
        tracks: List[Dict[str, Any]],
        style: str
    ) -> Optional[Dict[str, Any]]:
        """Generate setlist using Gemini AI."""
        import json
        
        # Build track summary for the prompt
        track_summary = []
        for i, t in enumerate(tracks):
            track_summary.append(
                f"{i+1}. \"{t.get('name', 'Unknown')}\" by {t.get('artists', 'Unknown')} | "
                f"BPM: {t.get('bpm', '?')} | Key: {t.get('camelot', '?')} | Energy: {t.get('energy', '?')}"
            )
        
        style_desc = {
            "progressive": "gradually build energy from low to high, creating a journey",
            "peak-time": "maintain high energy throughout with dramatic moments",
            "chill": "keep energy low to medium, prioritizing smooth vibes",
            "journey": "create a wave pattern - build up, peak, come down, build again"
        }.get(style, "gradually build energy")
        
        prompt = f"""You are an expert DJ creating an optimal setlist. Analyze these tracks and order them for the best flow.

TRACKS:
{chr(10).join(track_summary)}

GOAL: {style_desc}

MIXING RULES:
1. Harmonically compatible keys mix best (same Camelot number, or ±1, or A↔B switch)
2. Keep BPM changes within ±8 BPM between tracks for smooth mixing
3. Energy should follow the style pattern
4. Consider musical "story" - intro, build, peak, outro

DJ TECHNIQUES TO SUGGEST:
- "Long Blend" - 16-32 bar crossfade with EQ swapping
- "Filter Sweep" - Use low-pass or high-pass filter on outgoing track
- "Echo Out" - Apply echo/delay while fading out
- "Hard Cut" - Quick switch on phrase start (for genre changes or impact)
- "Beat Drop" - Drop incoming track on a breakdown/drop
- "EQ Swap" - Gradually swap bass/mids/highs between tracks
- "Loop & Build" - Loop outgoing track while bringing in new one
- "Acapella Blend" - If vocal track, layer over instrumental

Respond ONLY with valid JSON in this exact format:
{{
  "order": [1, 3, 2, ...],
  "tips": [
    {{
      "from": 1,
      "to": 3,
      "technique": "Filter Sweep",
      "timing": "16 bars",
      "tip": "Filter out the bass of track 1, bring in track 3 on the drop"
    }},
    ...
  ]
}}"""

        try:
            response = await self._model.generate_content_async(prompt)
            text = response.text.strip()
            
            # Extract JSON from response
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(text)
            order = data.get("order", [])
            tips = data.get("tips", [])
            
            # Map back to track IDs
            ordered_ids = []
            for idx in order:
                if 1 <= idx <= len(tracks):
                    ordered_ids.append(tracks[idx - 1].get("id"))
            
            # Map tips to track IDs
            suggestions = []
            for tip in tips:
                from_idx = tip.get("from", 0)
                to_idx = tip.get("to", 0)
                if 1 <= from_idx <= len(tracks) and 1 <= to_idx <= len(tracks):
                    t1 = tracks[from_idx - 1]
                    t2 = tracks[to_idx - 1]
                    suggestions.append({
                        "from_id": t1.get("id"),
                        "to_id": t2.get("id"),
                        "harmonic_match": self.is_harmonically_compatible(
                            t1.get("camelot", "?"), t2.get("camelot", "?")
                        ),
                        "bpm_diff": abs(t2.get("bpm", 0) - t1.get("bpm", 0)),
                        "technique": tip.get("technique", ""),
                        "timing": tip.get("timing", ""),
                        "tip": tip.get("tip", "")
                    })
            
            logger.info(f"AI generated setlist with {len(ordered_ids)} tracks")
            return {
                "ordered_ids": ordered_ids,
                "suggestions": suggestions,
                "method": "ai-gemini-2.0-flash"
            }
            
        except json.JSONDecodeError as e:
            logger.warning(f"Failed to parse AI response as JSON: {e}")
            return None
        except Exception as e:
            logger.error(f"AI generation error: {e}")
            return None


            return None
    
    async def get_audio_features_ai(self, name: str, artist: str) -> Optional[Dict[str, Any]]:
        """
        Estimate audio features using AI when Spotify data is unavailable.
        """
        if not self._init_genai() or not self._model:
            return None
        
        prompt = f"""Act as an expert musicologist and DJ.
Provide the OFFICIAL studio audio analysis for the track:
Title: "{name}"
Artist: "{artist}"

Analyze the genre and style. (e.g. Dubstep/Mid-tempo is usually 90-110 BPM, House is 120-130).
Provide the most accurate:
1. BPM (Integer) - Check for half-time/double-time ambiguities.
2. Key (Camelot Notation, e.g. 5A, 11B)
3. Energy (0.0 to 1.0)

Respond ONLY with valid JSON:
{{
  "bpm": 100,
  "camelot": "5A",
  "energy": 0.8
}}"""

        try:
            response = await self._model.generate_content_async(prompt)
            text = response.text.strip()
            
            # Extract JSON
            import json
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(text)
            
            # Validate
            return {
                "track_id": f"ai_{abs(hash(name + artist))}", # Dummy ID
                "bpm": int(data.get("bpm", 120)),
                "camelot": data.get("camelot", "?"),
                "energy": float(data.get("energy", 0.5)),
                "key": -1, # Unknown
                "mode": 0,
                "danceability": 0.5,
                "valence": 0.5,
                "source": "ai_estimate"
            }
            
        except Exception as e:
            logger.warning(f"AI audio features estimation failed (using fallback): {e}")
            return None
    
    async def interpret_mood_query(self, query: str) -> Optional[Dict[str, Any]]:
        """
        Interpret a natural language mood query using AI.
        Returns structured search terms and mood metadata.
        """
        if not self._init_genai() or not self._model:
            return None
        
        prompt = f"""You are a music discovery AI. The user wants to find music based on a mood or vibe description.

USER QUERY: "{query}"

Interpret this mood/vibe and provide:
1. 3-5 search terms that would find matching songs (artist names, genres, song characteristics)
2. Mood keywords that describe this vibe
3. Suggested BPM range
4. Energy level (low, medium, high)

Respond ONLY with valid JSON:
{{
  "search_terms": ["term1", "term2", "term3"],
  "moods": ["chill", "relaxed"],
  "bpm_range": {{"min": 70, "max": 100}},
  "energy": "low",
  "description": "Brief 1-sentence description of the vibe"
}}"""

        try:
            import json
            response = await self._model.generate_content_async(prompt)
            text = response.text.strip()
            
            # Extract JSON
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0].strip()
            elif "```" in text:
                text = text.split("```")[1].split("```")[0].strip()
            
            data = json.loads(text)
            logger.info(f"AI interpreted mood query: {query} -> {data.get('search_terms', [])}")
            return data
            
        except Exception as e:
            logger.warning(f"AI mood interpretation failed: {e}")
            return None


# Singleton instance
dj_service = DJService()
