import httpx
from app.core.config import settings

class DrivingService:
    async def get_route(self, origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float):
        url = f"https://api.mapbox.com/directions/v5/mapbox/driving/{origin_lon},{origin_lat};{dest_lon},{dest_lat}"
        
        params = {
            "overview": "full", 
            "geometries": "geojson",
            "access_token": settings.MAPBOX_API_KEY
        }

        async with httpx.AsyncClient() as client:
            try:
                print(f"🚗 Calculating Mapbox route from ({origin_lat},{origin_lon}) to ({dest_lat},{dest_lon})")
                
                response = await client.get(url, params=params, timeout=10.0)
                
                if response.status_code != 200:
                    return {"error": f"Mapbox API failed: {response.text}"}
                
                data = response.json()
                if data.get("code") != "Ok":
                    return {"error": "No viable driving route found between these locations"}

                route = data["routes"][0]
                distance_km = route["distance"] / 1000.0
                duration_mins = route["duration"] / 60.0

                result = {
                    "distance_km": round(distance_km, 2),
                    "duration_mins": round(duration_mins, 2),
                    "geometry": route["geometry"] 
                }
                
                return result
            except Exception as e:
                return {"error": f"Driving API Error: {str(e)}"}

driving_service = DrivingService()