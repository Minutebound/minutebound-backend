import httpx
from app.core.config import settings
from typing import List, Dict, Any

class SerpDestinationProvider:
    def __init__(self):
        self.api_key = settings.SERPAPI_KEY
        self.base_url = "https://serpapi.com/search.json"

    async def get_popular_destinations(self) -> List[Dict[str, Any]]:
        """Fetches trending US destinations using Google Search Top Sights."""
        params = {
            "engine": "google",
            "q": "popular travel destinations in USA",
            "api_key": self.api_key
        }
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.base_url, params=params, timeout=15.0)
                data = response.json()
                sights = data.get("top_sights", {}).get("sights", [])
                
                return [
                    {
                        "name": s.get("title"),
                        "description": s.get("description"),
                        "image_url": s.get("thumbnail"),
                        "link": s.get("link")
                    } for s in sights
                ]
            except Exception as e:
                print(f"SerpApi Destination Error: {e}")
                return []