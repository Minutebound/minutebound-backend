import httpx
import math
from app.services.base_amadeus_client import BaseAmadeusClient
from app.schemas.tour import Tour

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class AmadeusTourProvider(BaseAmadeusClient):
    async def get_tours_nearby(self, lat: float, lon: float, radius_miles: int = 30):
        radius_km = int(radius_miles * 1.60934)
        token = await self.get_token()
        if not token: return {"error": "Authentication Failed"}

        url = f"{self.base_url}/v1/shopping/activities"
        headers = {"Authorization": f"Bearer {token}"}
        params = {"latitude": lat, "longitude": lon, "radius": radius_km}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, params=params, timeout=30.0)
                if response.status_code != 200: return {"error": response.text}
                
                raw_data = response.json().get("data", [])
                clean_tours = []
                
                for item in raw_data:
                    pictures = item.get("pictures", [])
                    pic_url = pictures[0] if pictures else None
                    price_info = item.get("price", {})
                    
                    activity_lat = item.get("geoCode", {}).get("latitude")
                    activity_lon = item.get("geoCode", {}).get("longitude")
                    dist = calculate_distance(lat, lon, activity_lat, activity_lon) if activity_lat else 999.0

                    clean_tours.append(Tour(
                        id=item.get("id"),
                        name=item.get("name"),
                        short_description=item.get("shortDescription"),
                        geo_code=item.get("geoCode"),
                        price=float(price_info.get("amount", 0.0)),
                        currency=price_info.get("currencyCode", "USD"),
                        picture_url=pic_url,
                        minimum_duration=item.get("minimumDuration"),
                        distance_km=round(dist, 2)
                    ))

                clean_tours.sort(key=lambda x: x.distance_km)
                return clean_tours
            except Exception as e:
                return {"error": str(e)}