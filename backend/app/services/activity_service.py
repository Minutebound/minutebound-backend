import httpx
import math
from app.services.base_client import BaseAmadeusClient
from app.schemas.activity import Activity

def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

class ActivityService(BaseAmadeusClient):
    
    async def get_activities_nearby(self, lat: float, lon: float, radius_miles: int = 30):
        radius_km = int(radius_miles * 1.60934)

        token = await self.get_token()
        if not token:
            return {"error": "Authentication Failed"}

        url = f"{self.base_url}/v1/shopping/activities"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "latitude": lat,
            "longitude": lon,
            "radius": radius_km
        }

        async with httpx.AsyncClient() as client:
            try:
                print(f"🎢 Fetching activities near {lat}, {lon}")
                response = await client.get(url, headers=headers, params=params, timeout=30.0)
                
                if response.status_code != 200:
                    return {"error": response.text}
                
                raw_data = response.json().get("data", [])
                clean_activities = []
                
                for item in raw_data:
                    pictures = item.get("pictures", [])
                    pic_url = pictures[0] if pictures else None
                    
                    price_info = item.get("price", {})
                    price_amount = float(price_info.get("amount", 0.0))
                    currency = price_info.get("currencyCode", "USD")

                    activity_lat = item.get("geoCode", {}).get("latitude")
                    activity_lon = item.get("geoCode", {}).get("longitude")
                    dist = 999.0
                    if activity_lat and activity_lon:
                        dist = calculate_distance(lat, lon, activity_lat, activity_lon)

                    activity_obj = Activity(
                        id=item.get("id"),
                        name=item.get("name"),
                        short_description=item.get("shortDescription"),
                        geo_code=item.get("geoCode"),
                        price=price_amount,
                        currency=currency,
                        picture_url=pic_url,
                        minimum_duration=item.get("minimumDuration"),
                        distance_km=round(dist, 2)
                    )
                    clean_activities.append(activity_obj)

                clean_activities.sort(key=lambda x: x.distance_km)
                
                return clean_activities
            except Exception as e:
                return {"error": str(e)}

activity_service = ActivityService()