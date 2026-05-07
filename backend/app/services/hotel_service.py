import httpx
import math
import base64
import asyncio
from app.core.config import settings
from app.schemas.hotel import Hotel, HotelOffer
from app.services.location_service import location_service 


def calculate_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c

async def get_address_from_coords(client: httpx.AsyncClient, lat: float, lon: float) -> str:
    try:
        url = f"https://api-bdc.net/data/reverse-geocode?latitude={lat}&longitude={lon}&localityLanguage=en&key={settings.BDC_API_KEY}"
        
        resp = await client.get(url, timeout=5.0)
        
        if resp.status_code == 200:
            data = resp.json()
            locality = data.get("locality", "")
            city = data.get("city", "")
            principal = data.get("principalSubdivision", "")
            country = data.get("countryName", "")
            
            parts = []
            if locality and locality != city: parts.append(locality)
            if city: parts.append(city)
            if principal and principal not in parts: parts.append(principal)
            if country: parts.append(country)
            
            if parts:
                return ", ".join(parts)
        else:
            print(f"⚠️ Reverse Geocode Failed (Status {resp.status_code}): {resp.text}")
    except Exception as e:
        print(f"❌ Geocoding Error: {str(e)}")
    return None

class HotelService:
    def __init__(self):
        self.api_key = settings.SERPAPI_KEY
        self.base_url = "https://serpapi.com/search.json"

    async def get_available_hotels_by_geocode(self, lat: float, lon: float, check_in_date: str, check_out_date: str, adults: int, radius: int = 50):
        print(f"🏨 [HOTELS] Fetching available hotels near {lat}, {lon} via SerpApi")
        
        if not self.api_key:
            return {"error": "SerpAPI Key is missing from configuration."}

        adults = max(1, min(int(adults), 9))

        async with httpx.AsyncClient() as client:
            try:
                location_name = await get_address_from_coords(client, lat, lon)
                
                if location_name:
                    query = f"Hotels in {location_name}"
                else:
                    query = f"{lat},{lon}" 
                
                print(f"🔍 SerpApi Query: {query}")
                
                params = {
                    "engine": "google_hotels",
                    "q": query,
                    "check_in_date": check_in_date,
                    "check_out_date": check_out_date,
                    "adults": adults,
                    "currency": "USD",
                    "gl": "us",
                    "hl": "en",
                    "api_key": self.api_key
                }

                response = await client.get(self.base_url, params=params, timeout=30.0)
                
                if response.status_code != 200:
                    return {"error": f"SerpApi Error: {response.text}"}
                
                data = response.json()
                properties = data.get("properties", [])
                
                if not properties:
                    iata = await location_service.get_nearest_airport(lat, lon)
                    if iata:
                        print(f"⚠️ No hotels found, falling back to airport code: {iata}")
                        params["q"] = f"Hotels near {iata} airport"
                        fallback_response = await client.get(self.base_url, params=params, timeout=30.0)
                        properties = fallback_response.json().get("properties", [])

                async def enrich_property(prop):
                    address_text = prop.get("address") or prop.get("neighborhood")
                    if not address_text:
                        coords = prop.get("gps_coordinates", {})
                        p_lat = coords.get("latitude")
                        p_lon = coords.get("longitude")
                        if p_lat and p_lon:
                            fetched_addr = await get_address_from_coords(client, p_lat, p_lon)
                            if fetched_addr:
                                prop["address"] = fetched_addr
                    return prop
                
                properties = await asyncio.gather(*(enrich_property(p) for p in properties))

                clean_available_hotels = []
                for prop in properties:
                    hotel_id = prop.get("property_token")
                    if not hotel_id:
                        hotel_id = base64.b64encode(prop.get("name", "Unknown").encode()).decode()

                    coords = prop.get("gps_coordinates", {})
                    prop_lat = coords.get("latitude")
                    prop_lon = coords.get("longitude")
                    
                    address_text = prop.get("address")
                    amadeus_formatted_address = {"lines": [address_text]} if address_text else {"lines": ["Location provided upon booking"]}

                    raw_rating = prop.get("overall_rating")
                    safe_rating = int(round(raw_rating)) if raw_rating else None

                    clean_available_hotels.append(Hotel(
                        chain_code=None,
                        iata_code=None,
                        hotel_id=hotel_id,
                        name=prop.get("name", "Unknown Hotel"),
                        geo_code={"latitude": prop_lat, "longitude": prop_lon} if prop_lat else None,
                        rating=safe_rating,
                        distance_km=None,
                        address=amadeus_formatted_address
                    ))
                    
                    if len(clean_available_hotels) >= 40:
                        break

                print(f"✅ Found {len(clean_available_hotels)} hotels.")
                return clean_available_hotels
            except Exception as e:
                print(f"🔥 Hotel Service Error: {str(e)}")
                return {"error": str(e)}

    async def get_specific_hotel_offer(self, hotel_id: str, check_in_date: str, check_out_date: str, adults: int):
        print(f"🛏️ [HOTEL OFFER] Fetching price for Hotel ID: {hotel_id}")
        
        if not self.api_key:
            return {"error": "SerpAPI Key is missing from configuration."}

        adults = max(1, min(int(adults), 9))
        is_token = False
        query = "Hotel"
        if hotel_id.startswith("Ch"):
            is_token = True
        else:
            try:
                decoded = base64.b64decode(hotel_id).decode('utf-8')
                if decoded.isprintable():
                    query = decoded
            except Exception:
                pass 

        params = {
            "engine": "google_hotels",
            "q": query,
            "check_in_date": check_in_date,
            "check_out_date": check_out_date,
            "adults": adults,
            "currency": "USD",
            "gl": "us",
            "hl": "en",
            "api_key": self.api_key
        }

        if is_token:
            params["property_token"] = hotel_id

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(self.base_url, params=params, timeout=30.0)
                if response.status_code != 200:
                    return {"error": f"SerpApi Error: {response.text}"}

                data = response.json()
                
                if "property_token" in data or "rate_per_night" in data:
                    item = data
                else:
                    properties = data.get("properties", [])
                    if not properties:
                        return {"error": "Offer expired or not available."}
                    item = properties[0] 
                
                rate = item.get("rate_per_night", {})
                price = rate.get("extracted_lowest", 0.0)
                if price == 0.0:
                    total_rate = item.get("total_rate", {})
                    price = total_rate.get("extracted_lowest", 0.0)
                
                hotel_description = item.get("description", "Comfortable room at the lowest available nightly rate.")
                hotel_amenities = item.get("amenities", [])
                
                exact_address = item.get("address")
                formatted_offer_address = {"lines": [exact_address]} if exact_address else None

                rooms = [{
                    "room_name": "Standard Room", 
                    "description": hotel_description, 
                    "category": "Room", 
                    "bed_type": "Standard", 
                    "beds_count": 1,        
                    "price": price,         
                    "currency": "USD",
                    "amenities": hotel_amenities 
                }]

                return HotelOffer(
                    hotel_id=hotel_id,
                    name=item.get("name"),
                    check_in_date=check_in_date,
                    check_out_date=check_out_date,
                    guests=adults,
                    price=float(price),
                    currency="USD",
                    latitude=item.get("gps_coordinates", {}).get("latitude"),
                    longitude=item.get("gps_coordinates", {}).get("longitude"),
                    address=formatted_offer_address,
                    rooms=rooms
                ).model_dump()

            except Exception as e:
                return {"error": str(e)}

hotel_service = HotelService()