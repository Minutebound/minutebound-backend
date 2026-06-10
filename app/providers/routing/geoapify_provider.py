import httpx
from app.core.config import settings

class GeoapifyRoutingProvider:
    async def get_route(self, origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float):
        url = f"https://api.geoapify.com/v1/routing?waypoints={origin_lat},{origin_lon}|{dest_lat},{dest_lon}&mode=drive&apiKey={settings.GEOAPIFY_API_KEY}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, timeout=10.0)
            if response.status_code != 200:
                return {"error": "Geoapify API failed"}
                
            data = response.json()
            if "features" not in data or len(data["features"]) == 0:
                return {"error": "No viable route found by Geoapify"}
                
            route = data["features"][0]["properties"]
            return {
                "distance_km": round(route["distance"] / 1000.0, 2),
                "duration_mins": round(route["time"] / 60.0, 2),
                "geometry": data["features"][0]["geometry"]
            }