import httpx
from app.services.base_amadeus_client import BaseAmadeusClient
from app.schemas.stay import Stay, StayOffer

class AmadeusStayProvider(BaseAmadeusClient):
    async def get_available_hotels_by_geocode(self, lat: float, lon: float, check_in_date: str, check_out_date: str, adults: int, radius: int = 50):
        token = await self.get_token()
        if not token:
            return {"error": "Amadeus authentication failed"}
        
        url = f"{self.base_url}/v1/reference-data/locations/hotels/by-geocode"
        headers = {"Authorization": f"Bearer {token}"}
        
        safe_radius = min(radius, 300)
        params = {
            "latitude": lat,
            "longitude": lon,
            "radius": safe_radius, 
            "radiusUnit": "MILE"
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, params=params, timeout=20.0)
                if response.status_code != 200:
                    return {"error": f"Amadeus API Error: {response.text}"}
                
                data = response.json()
                hotels_data = data.get("data", [])
                
                if not hotels_data:
                    return []
                
                clean_hotels = []
                for h in hotels_data[:40]: 
                    geo = h.get("geoCode", {})
                    rating = h.get("rating")
                    
                    parsed_rating = int(rating) if rating and str(rating).isdigit() else None

                    address_lines = []
                    addr_info = h.get("address", {})
                    if "cityName" in addr_info:
                        address_lines.append(addr_info["cityName"])

                    # CHANGED FROM Hotel() to Stay()
                    clean_hotels.append(Stay(
                        hotel_id=h.get("hotelId"),
                        name=h.get("name", "Unknown Hotel"),
                        geo_code={"latitude": geo.get("latitude"), "longitude": geo.get("longitude")} if geo else None,
                        rating=parsed_rating,
                        address={"lines": address_lines} if address_lines else {"lines": ["Location provided upon booking"]}
                    ))
                    
                return clean_hotels
            except Exception as e:
                return {"error": f"Amadeus Geocode Request Failed: {str(e)}"}

    async def get_specific_hotel_offer(self, hotel_id: str, check_in_date: str, check_out_date: str, adults: int):
        token = await self.get_token()
        if not token:
            return {"error": "Amadeus authentication failed"}

        url = f"{self.base_url}/v3/shopping/hotel-offers"
        headers = {"Authorization": f"Bearer {token}"}
        params = {
            "hotelIds": hotel_id,
            "adults": max(1, min(int(adults), 9)),
            "checkInDate": check_in_date,
            "checkOutDate": check_out_date,
            "currency": "USD"
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, params=params, timeout=20.0)
                if response.status_code != 200:
                    return {"error": f"Amadeus API Error: {response.text}"}
                
                data = response.json()
                offers_data = data.get("data", [])
                
                if not offers_data:
                    return {"error": "No offers available for this hotel on these dates."}
                
                hotel_info = offers_data[0].get("hotel", {})
                offers = offers_data[0].get("offers", [])
                
                if not offers:
                    return {"error": "No specific room offers found."}
                    
                best_offer = offers[0]
                price = float(best_offer.get("price", {}).get("total", 0.0))
                currency = best_offer.get("price", {}).get("currency", "USD")
                room_desc = best_offer.get("room", {}).get("description", {}).get("text", "Standard Room")
                room_category = best_offer.get("room", {}).get("typeEstimated", {}).get("category", "ROOM")
                
                # CHANGED FROM HotelOffer() to StayOffer()
                return StayOffer(
                    hotel_id=hotel_info.get("hotelId", hotel_id),
                    name=hotel_info.get("name", "Unknown Hotel"),
                    check_in_date=check_in_date,
                    check_out_date=check_out_date,
                    guests=adults,
                    price=price,
                    currency=currency,
                    address={"lines": [hotel_info.get("cityCode", "")]} if hotel_info.get("cityCode") else None,
                    rooms=[{
                        "room_name": room_category,
                        "description": room_desc,
                        "price": price,
                        "currency": currency,
                        "amenities": best_offer.get("amenities", [])
                    }]
                ).model_dump()
            except Exception as e:
                return {"error": f"Amadeus Offer Request Failed: {str(e)}"}