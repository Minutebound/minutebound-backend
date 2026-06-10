import httpx
from app.core.config import settings

class GeoapifyAttractionProvider:
    def __init__(self):
        self.api_key = settings.GEOAPIFY_API_KEY
        self.base_url = "https://api.geoapify.com/v2/places"

    async def get_attractions(self, lat: float, lon: float, radius_miles: int = 30):
        if not self.api_key:
            return {"error": "Geoapify API key is missing"}

        # Convert miles to meters for Geoapify
        radius_meters = int(radius_miles * 1609.34)
        
        # Categories requested: tourism, adult, activity
        categories = "tourism,adult,activity"
        
        params = {
            "categories": categories,
            "filter": f"circle:{lon},{lat},{radius_meters}",
            "bias": f"proximity:{lon},{lat}",
            "limit": 30,
            "apiKey": self.api_key
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.base_url, params=params, timeout=15.0)
                if response.status_code != 200:
                    return {"error": f"Geoapify Error: {response.text}"}
                
                features = response.json().get("features", [])
                clean_attractions = []
                
                for feature in features:
                    props = feature.get("properties", {})
                    
                    # Ensure it actually has a name before adding it
                    name = props.get("name")
                    if not name:
                        continue
                        
                    clean_attractions.append({
                        "id": props.get("place_id"),
                        "name": name,
                        "category": props.get("categories", ["Unknown"])[0],
                        "address": props.get("formatted"),
                        "distance_meters": props.get("distance"),
                        "website": props.get("website"),
                        "latitude": props.get("lat"),
                        "longitude": props.get("lon")
                    })
                
                return clean_attractions
            except Exception as e:
                return {"error": f"Failed to fetch attractions: {str(e)}"}