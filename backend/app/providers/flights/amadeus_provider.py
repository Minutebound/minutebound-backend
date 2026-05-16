import httpx
from app.services.base_amadeus_client import BaseAmadeusClient
from app.schemas.flight import FlightOffer, FlightItinerary, FlightSegment, Amenities

class AmadeusFlightProvider(BaseAmadeusClient):
    async def get_flights(self, origin: str, destination: str, date: str, return_date: str, adults: int, travel_class: str = "ECONOMY", children: int = 0):
        token = await self.get_token()
        if not token: 
            return {"error": "Amadeus Authentication Failed"}

        url = f"{self.base_url}/v2/shopping/flight-offers"
        headers = {"Authorization": f"Bearer {token}"}
        
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
            "max": 20 # Note: The Amadeus Test API often only returns 1-2 cached flights despite this.
        }
        
        if return_date: params["returnDate"] = return_date
        if children > 0: params["children"] = children

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(url, headers=headers, params=params, timeout=30.0)
                if response.status_code != 200: 
                    return {"error": f"Amadeus API Error: {response.text}"}
                
                raw_data = response.json()
                offers = raw_data.get("data", [])
                
                dictionaries = raw_data.get("dictionaries", {})
                carriers = dictionaries.get("carriers", {})
                aircraft_dict = dictionaries.get("aircraft", {})

                clean_offers = []
                
                for offer in offers:
                    price_info = offer.get("price", {})
                    total_price = float(price_info.get("total", 0.0))
                    
                    # Extract baggage and cabin details per segment from traveler pricings
                    traveler_pricings = offer.get("travelerPricings", [{}])[0]
                    fare_details = {
                        fd.get("segmentId"): fd 
                        for fd in traveler_pricings.get("fareDetailsBySegment", [])
                    }

                    itineraries = []
                    primary_airline_code = "UNKNOWN"
                    primary_airline_name = "UNKNOWN"

                    for itin in offer.get("itineraries", []):
                        formatted_duration = itin.get("duration", "").replace("PT", "").replace("H", "H ").replace("M", "M")
                        
                        segments = []
                        for seg in itin.get("segments", []):
                            carrier_code = seg.get("carrierCode", "UNKNOWN")
                            carrier_name = carriers.get(carrier_code, carrier_code)
                            seg_id = seg.get("id")
                            
                            if primary_airline_code == "UNKNOWN":
                                primary_airline_code = carrier_code
                                primary_airline_name = carrier_name

                            # Deep Parsing
                            fare_info = fare_details.get(seg_id, {})
                            checked_bags = fare_info.get("includedCheckedBags", {}).get("quantity", 0)
                            seg_cabin = fare_info.get("cabin", travel_class_formatted)
                            
                            aircraft_code = seg.get("aircraft", {}).get("code")
                            aircraft_name = aircraft_dict.get(aircraft_code, aircraft_code)
                            
                            seg_duration = seg.get("duration", "").replace("PT", "").replace("H", "H ").replace("M", "M")

                            segments.append(FlightSegment(
                                departure_airport=seg.get("departure", {}).get("iataCode", "TBA"),
                                departure_terminal=seg.get("departure", {}).get("terminal"),
                                departure_time=seg.get("departure", {}).get("at", "TBA"),
                                arrival_airport=seg.get("arrival", {}).get("iataCode", "TBA"),
                                arrival_terminal=seg.get("arrival", {}).get("terminal"),
                                arrival_time=seg.get("arrival", {}).get("at", "TBA"),
                                carrier_code=carrier_code,
                                carrier_name=carrier_name,
                                flight_number=str(seg.get("number", "TBA")),
                                aircraft=aircraft_name,
                                duration=seg_duration,
                                cabin_class=seg_cabin,
                                checked_bags=checked_bags,
                                amenities=Amenities()
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
                        raw_offer_data=offer, # <-- CRITICAL FIX FOR THE 400 BOOKING ERROR
                        itineraries=itineraries
                    ))

                return clean_offers if clean_offers else {"error": "No viable flights found by Amadeus."}
                
            except Exception as e:
                return {"error": str(e)}

    async def confirm_price_and_policies(self, flight_offer: dict):
        token = await self.get_token()
        if not token: return {"error": "Authentication Failed"}

        url = f"{self.base_url}/v1/shopping/flight-offers/pricing"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
        
        payload = {"data": {"type": "flight-offers-pricing", "flightOffers": [flight_offer]}}

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=30.0)
                if response.status_code != 200:
                    return {"error": f"Pricing API Error: {response.text}"}
                
                raw_data = response.json()
                priced_offer = raw_data["data"]["flightOffers"][0]
                
                policies = []
                for traveler in priced_offer.get("travelerPricings", []):
                    for segment in traveler.get("fareDetailsBySegment", []):
                        for penalty in segment.get("penalties", []):
                            policies.append({
                                "type": penalty.get("type"), 
                                "allowed": penalty.get("applicability") == "ALLOWED",
                                "fee": penalty.get("amount"),
                                "currency": priced_offer["price"]["currency"]
                            })
                
                return {
                    "priced_offer": priced_offer, 
                    "policies": policies
                }
            except Exception as e:
                return {"error": str(e)}

    async def book_flight(self, priced_offer: dict, travelers: list):
        token = await self.get_token()
        if not token: return {"error": "Authentication Failed"}

        url = f"{self.base_url}/v1/booking/flight-orders"
        headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

        payload = {
            "data": {
                "type": "flight-order",
                "flightOffers": [priced_offer],
                "travelers": travelers
            }
        }

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(url, headers=headers, json=payload, timeout=30.0)
                if response.status_code not in [200, 201]:
                    return {"error": f"Booking API Error: {response.text}"}
                
                booking_data = response.json()
                pnr = booking_data["data"]["associatedRecords"][0]["reference"]
                booking_id = booking_data["data"]["id"]
                
                return {
                    "status": "SUCCESS",
                    "pnr": pnr,
                    "booking_id": booking_id,
                    "raw_order": booking_data
                }
            except Exception as e:
                return {"error": str(e)}