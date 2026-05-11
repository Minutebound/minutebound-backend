import httpx
from app.services.base_amadeus_client import BaseAmadeusClient
from app.schemas.flight import FlightOffer, FlightItinerary, FlightSegment

class AmadeusFlightProvider(BaseAmadeusClient):
    async def search_flights(self, origin: str, destination: str, date: str, return_date: str, adults: int, travel_class: str = "ECONOMY", children: int = 0):
        # 1. Authenticate with Amadeus
        token = await self.get_token()
        if not token: 
            return {"error": "Amadeus Authentication Failed"}

        # 2. Setup the Request
        url = f"{self.base_url}/v2/shopping/flight-offers"
        headers = {"Authorization": f"Bearer {token}"}
        
        # Amadeus requires uppercase enum values for travel class
        travel_class_formatted = travel_class.upper().replace(" ", "_")
        if travel_class_formatted not in ["ECONOMY", "PREMIUM_ECONOMY", "BUSINESS", "FIRST"]:
            travel_class_formatted = "ECONOMY"

        params = {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": date,
            "adults": adults,
            "travelClass": travel_class_formatted,
            "currencyCode": "USD",
            "max": 20 # Limit to top 20 to keep response times fast
        }
        
        if return_date:
            params["returnDate"] = return_date
        if children > 0:
            params["children"] = children

        # 3. Execute request and parse data
        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, params=params, timeout=30.0)
                
                if response.status_code != 200: 
                    return {"error": f"Amadeus API Error: {response.text}"}
                
                raw_data = response.json()
                offers = raw_data.get("data", [])
                
                # Amadeus provides airline names in a separate dictionary
                dictionaries = raw_data.get("dictionaries", {})
                carriers = dictionaries.get("carriers", {})

                clean_offers = []
                
                for offer in offers:
                    price_info = offer.get("price", {})
                    total_price = float(price_info.get("total", 0.0))
                    
                    itineraries = []
                    primary_airline_code = "UNKNOWN"
                    primary_airline_name = "UNKNOWN"

                    # Parse Outbound (and Return if it exists) Itineraries
                    for itin in offer.get("itineraries", []):
                        # Amadeus returns duration like "PT14H15M"
                        raw_duration = itin.get("duration", "")
                        formatted_duration = raw_duration.replace("PT", "").replace("H", "H ").replace("M", "M")
                        
                        segments = []
                        for seg in itin.get("segments", []):
                            carrier_code = seg.get("carrierCode", "UNKNOWN")
                            carrier_name = carriers.get(carrier_code, carrier_code)
                            
                            # Grab the first airline as the primary for the whole ticket
                            if primary_airline_code == "UNKNOWN":
                                primary_airline_code = carrier_code
                                primary_airline_name = carrier_name

                            segments.append(FlightSegment(
                                departure_airport=seg.get("departure", {}).get("iataCode", "TBA"),
                                departure_time=seg.get("departure", {}).get("at", "TBA"),
                                arrival_airport=seg.get("arrival", {}).get("iataCode", "TBA"),
                                arrival_time=seg.get("arrival", {}).get("at", "TBA"),
                                carrier_code=carrier_code,
                                carrier_name=carrier_name,
                                flight_number=str(seg.get("number", "TBA"))
                            ))
                        
                        itineraries.append(FlightItinerary(
                            duration=formatted_duration,
                            stops=max(0, len(segments) - 1),
                            segments=segments
                        ))

                    clean_offers.append(FlightOffer(
                        id=offer.get("id", ""),
                        price=total_price,
                        currency=price_info.get("currency", "USD"),
                        airline_code=primary_airline_code,
                        airline_name=primary_airline_name,
                        cabin_class=travel_class_formatted,
                        itineraries=itineraries
                    ))

                if not clean_offers:
                    return {"error": "No viable flights found by Amadeus."}

                return clean_offers
                
            except Exception as e:
                return {"error": str(e)}