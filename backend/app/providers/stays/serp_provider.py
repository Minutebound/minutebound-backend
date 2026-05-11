import httpx
import base64
import asyncio
from app.core.config import settings
from app.schemas.stay import Stay, StayOffer
from app.services.location_service import location_service 

async def get_address_from_coords(client: httpx.AsyncClient, lat: float, lon: float) -> str:
    try:
        url = f"https://api-bdc.net/data/reverse-geocode?latitude={lat}&longitude={lon}&localityLanguage=en&key={settings.BDC_API_KEY}"
        resp = await client.get(url, timeout=5.0)
        if resp.status_code == 200:
            data = resp.json()
            parts = [p for p in [data.get("locality"), data.get("city"), data.get("principalSubdivision"), data.get("countryName")] if p]
            if parts: return ", ".join(list(dict.fromkeys(parts)))
    except Exception: pass
    return None

class SerpStayProvider:
    def __init__(self):
        self.api_key = settings.SERPAPI_KEY
        self.base_url = "https://serpapi.com/search.json"

    async def get_available_hotels_by_geocode(self, lat: float, lon: float, check_in_date: str, check_out_date: str, adults: int, radius: int = 50):
        if not self.api_key: return {"error": "SerpAPI Key missing"}
        adults = max(1, min(int(adults), 9))

        async with httpx.AsyncClient() as client:
            try:
                location_name = await get_address_from_coords(client, lat, lon)
                query = f"Hotels in {location_name}" if location_name else f"{lat},{lon}" 
                params = {"engine": "google_hotels", "q": query, "check_in_date": check_in_date, "check_out_date": check_out_date, "adults": adults, "currency": "USD", "gl": "us", "hl": "en", "api_key": self.api_key}

                response = await client.get(self.base_url, params=params, timeout=30.0)
                if response.status_code != 200: 
                    # SerpApi Error often means invalid dates or query
                    return {"error": f"SerpApi Error: {response.text}"}
                
                properties = response.json().get("properties", [])
                
                if not properties:
                    iata = await location_service.get_nearest_airport(lat, lon)
                    if iata:
                        params["q"] = f"Hotels near {iata} airport"
                        properties = (await client.get(self.base_url, params=params, timeout=30.0)).json().get("properties", [])

                clean_hotels = []
                for prop in properties[:40]:
                    hotel_id = prop.get("property_token") or base64.b64encode(prop.get("name", "Unknown").encode()).decode()
                    coords = prop.get("gps_coordinates", {})
                    addr = prop.get("address")
                    
                    # CHANGED FROM Hotel() to Stay()
                    clean_hotels.append(Stay(
                        hotel_id=hotel_id,
                        name=prop.get("name", "Unknown Hotel"),
                        geo_code={"latitude": coords.get("latitude"), "longitude": coords.get("longitude")} if coords else None,
                        rating=int(round(prop.get("overall_rating"))) if prop.get("overall_rating") else None,
                        address={"lines": [addr]} if addr else {"lines": ["Location provided upon booking"]}
                    ))
                return clean_hotels
            except Exception as e:
                return {"error": str(e)}

    async def get_specific_hotel_offer(self, hotel_id: str, check_in_date: str, check_out_date: str, adults: int):
        if not self.api_key: return {"error": "SerpAPI Key missing"}
        query = hotel_id if not hotel_id.startswith("Ch") else "Hotel"
        
        try:
            if not hotel_id.startswith("Ch") and base64.b64decode(hotel_id).decode('utf-8').isprintable():
                query = base64.b64decode(hotel_id).decode('utf-8')
        except Exception: pass

        params = {"engine": "google_hotels", "q": query, "check_in_date": check_in_date, "check_out_date": check_out_date, "adults": adults, "currency": "USD", "gl": "us", "hl": "en", "api_key": self.api_key}
        if hotel_id.startswith("Ch"): params["property_token"] = hotel_id

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.base_url, params=params, timeout=30.0)
                if response.status_code != 200: return {"error": f"SerpApi Error: {response.text}"}

                data = response.json()
                item = data if "rate_per_night" in data else data.get("properties", [{}])[0]
                if not item: return {"error": "Offer expired"}
                
                price = item.get("rate_per_night", {}).get("extracted_lowest", item.get("total_rate", {}).get("extracted_lowest", 0.0))
                
                # CHANGED FROM HotelOffer() to StayOffer()
                return StayOffer(
                    hotel_id=hotel_id,
                    name=item.get("name"),
                    check_in_date=check_in_date,
                    check_out_date=check_out_date,
                    guests=adults,
                    price=float(price),
                    currency="USD",
                    address={"lines": [item.get("address")]} if item.get("address") else None,
                    rooms=[{"room_name": "Standard Room", "description": item.get("description"), "price": price, "currency": "USD", "amenities": item.get("amenities", [])}]
                ).model_dump()
            except Exception as e:
                return {"error": str(e)}