import httpx
from app.services.base_client import BaseAmadeusClient
from app.core.config import settings  
class LocationService(BaseAmadeusClient):
    async def search_locations(self, keyword: str):
        token = await self.get_token()
        if not token:
            return []

        url = f"{self.base_url}/v1/reference-data/locations/cities"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "keyword": keyword,
            "countryCode": "US",
            "max": 10
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, params=params, timeout=10.0)
                if response.status_code != 200:
                    return []
                return response.json().get("data", [])
            except Exception:
                return []

    async def get_nearest_airport(self, lat: float, lon: float):
        """Fetches the nearest major commercial airport to a given lat/lon using AirLabs."""
        print(f"📍 Finding the best major airport for {lat}, {lon} via AirLabs...")
        
        url = "https://airlabs.co/api/v9/nearby"
        
        params = {
            "lat": lat,
            "lng": lon,
            "distance": 500,
            "api_key": settings.AIRLABS_API_KEY 
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, params=params, timeout=15.0)
                if response.status_code == 200:
                    data = response.json()
                    airports = data.get("response", {}).get("airports", [])
                    
                    if not airports:
                        return None

                    valid_airports = [
                        apt for apt in airports 
                        if apt.get("iata_code") is not None
                    ]
                    
                    if not valid_airports:
                        return None
                        
                    valid_airports.sort(key=lambda x: x.get("distance", float('inf')))
                    
                    nearby_pool = valid_airports[:10]
                    
                    nearby_pool.sort(key=lambda x: x.get("popularity", 0), reverse=True)
                    
                    best_match = nearby_pool[0]
                    best_iata = best_match.get("iata_code")
                    
                    print(f"✅ Selected Major Airport: {best_iata} ({best_match.get('name')}) - {best_match.get('distance')}km away")
                    return best_iata

            except Exception as e:
                print(f"❌ Error fetching nearest airport from AirLabs: {e}")
                
        return None

location_service = LocationService()