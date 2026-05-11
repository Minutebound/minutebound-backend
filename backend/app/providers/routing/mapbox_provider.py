import httpx
from app.core.config import settings

class MapboxRoutingProvider:
    async def get_route(self, origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float):
        url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
        params = {"overview": "full", "geometries": "geojson", "access_token": settings.MAPBOX_API_KEY}

        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=10.0)
            if response.status_code != 200:
                return {"error": f"Mapbox API failed: {response.text}"}
            
            data = response.json()
            if data.get("code") != "Ok": return {"error": "No viable route"}

            route = data["routes"][0]
            return {
                "distance_km": round(route["distance"] / 1000.0, 2),
                "duration_mins": round(route["duration"] / 60.0, 2),
                "geometry": route["geometry"]
            }