import httpx
import asyncio
import airportsdata
from app.core.config import settings
from app.schemas.flight import FlightOffer, FlightSegment, FlightItinerary

class FlightService:
    
    def __init__(self):
        self.airports_dict = airportsdata.load('IATA')
        self.api_key = settings.SERPAPI_KEY
        self.base_url = "https://serpapi.com/search.json"

    def get_airport_name(self, iata_code: str) -> str:
        """Instantly resolves the IATA code from the local database in O(1) time."""
        if not iata_code or iata_code == "TBA":
            return "Airport"
            
        code_upper = iata_code.upper()
        airport_info = self.airports_dict.get(code_upper)
        
        if airport_info:
            return airport_info.get("name", code_upper)
            
        return code_upper

    def _parse_flight_data(self, raw_data: dict, expected_class: str) -> list[FlightOffer]:
        """Parses a ONE-WAY Google Flights JSON from SerpApi into our Pydantic schemas."""
        clean_results = []
        
        raw_flights = raw_data.get("best_flights", []) + raw_data.get("other_flights", [])

        for idx, offer in enumerate(raw_flights):
            try:
                price = float(offer.get("price", 0.0))
                if price == 0.0:
                    continue

                segments_data = offer.get("flights", [])
                if not segments_data:
                    continue

                clean_segments = []
                for seg in segments_data:
                    dep = seg.get("departure_airport", {})
                    arr = seg.get("arrival_airport", {})
                    airline_name = seg.get("airline", "UNKNOWN")

                    flight_seg = FlightSegment(
                        departure_airport=dep.get("id", "TBA"),
                        departure_airport_name=None, 
                        departure_time=dep.get("time", "TBA"),
                        arrival_airport=arr.get("id", "TBA"),
                        arrival_airport_name=None, 
                        arrival_time=arr.get("time", "TBA"),
                        carrier_code=airline_name, 
                        carrier_name=airline_name,  
                        flight_number=str(seg.get("flight_number", "TBA")),
                        personal_item=1,
                        cabin_bags=1,
                        checked_bags=0 
                    )
                    clean_segments.append(flight_seg)

                duration_mins = offer.get("total_duration", 0)
                formatted_duration = f"{duration_mins // 60}H {duration_mins % 60}M" if duration_mins else "N/A"
                
                itinerary = FlightItinerary(
                    duration=formatted_duration,
                    stops=max(0, len(clean_segments) - 1),
                    segments=clean_segments
                )

                main_airline = clean_segments[0].carrier_name if clean_segments else "UNKNOWN"

                flight_obj = FlightOffer(
                    id=f"serpapi_leg_{idx}", 
                    price=price,
                    currency="USD",
                    airline_code=main_airline,
                    airline_name=main_airline,    
                    cabin_class=expected_class,        
                    itineraries=[itinerary] 
                )
                clean_results.append(flight_obj)

            except Exception as e:
                print(f"Error parsing flight segment: {e}")
                continue
        
        return clean_results

    async def search_flights(self, origin: str, destination: str, date: str, return_date: str, adults: int, travel_class: str = "ECONOMY", children: int = 0):
        print(f"✈️ Fetching flights via SerpApi (Stitching Method): {origin} <-> {destination}")
        
        if not self.api_key:
            return {"error": "SerpApi Key not configured in .env"}

        classes_to_search = [c.strip().upper() for c in travel_class.split(",")]
        travel_class_map = {"ECONOMY": "1", "PREMIUM_ECONOMY": "2", "BUSINESS": "3", "FIRST": "4"}
        
        async def fetch_for_class(t_class):
            mapped_class = travel_class_map.get(t_class, "1")
            
            base_params = {
                "engine": "google_flights",
                "currency": "USD",
                "hl": "en",
                "adults": adults,
                "travel_class": mapped_class,
                "api_key": self.api_key,
                "type": "2" 
            }
            if children > 0: base_params["children"] = children

            outbound_params = {**base_params, "departure_id": origin, "arrival_id": destination, "outbound_date": date}
            
            async with httpx.AsyncClient() as client:
                requests = [client.get(self.base_url, params=outbound_params, timeout=30.0)]
                
                if return_date:
                    return_params = {**base_params, "departure_id": destination, "arrival_id": origin, "outbound_date": return_date}
                    requests.append(client.get(self.base_url, params=return_params, timeout=30.0))

                responses = await asyncio.gather(*requests, return_exceptions=True)
                
                outbound_offers = []
                if not isinstance(responses[0], Exception) and responses[0].status_code == 200:
                    outbound_offers = self._parse_flight_data(responses[0].json(), t_class)

                if return_date and len(responses) == 2:
                    return_offers = []
                    if not isinstance(responses[1], Exception) and responses[1].status_code == 200:
                        return_offers = self._parse_flight_data(responses[1].json(), t_class)
                    
                    combined_results = []
                    for outbound, inbound in zip(outbound_offers, return_offers):
                        outbound.price += inbound.price 
                        outbound.itineraries.extend(inbound.itineraries) 
                        combined_results.append(outbound)
                    return combined_results

                return outbound_offers

        tasks = [fetch_for_class(c) for c in classes_to_search]
        class_results = await asyncio.gather(*tasks)

        final_flights = []
        seen_signatures = set()

        for res_list in class_results:
            if isinstance(res_list, list):
                for flight in res_list:
                    try:
                        first_fn = flight.itineraries[0].segments[0].flight_number
                        signature = f"{flight.price}_{flight.airline_code}_{first_fn}_{flight.cabin_class}"
                    except (IndexError, AttributeError):
                        signature = flight.id
                    
                    if signature not in seen_signatures:
                        seen_signatures.add(signature)
                        flight.id = f"flight_{len(seen_signatures)}"
                        final_flights.append(flight)
        
        unique_iata = {seg.departure_airport for f in final_flights for i in f.itineraries for seg in i.segments if seg.departure_airport and seg.departure_airport != "TBA"}
        unique_iata.update({seg.arrival_airport for f in final_flights for i in f.itineraries for seg in i.segments if seg.arrival_airport and seg.arrival_airport != "TBA"})
        
        airport_info_map = {code: self.airports_dict.get(code.upper(), {}) for code in unique_iata}

        for flight in final_flights:
            for itin in flight.itineraries:
                for seg in itin.segments:
                    dep_info = airport_info_map.get(seg.departure_airport, {})
                    arr_info = airport_info_map.get(seg.arrival_airport, {})
                    
                    seg.departure_airport_name = dep_info.get("name", seg.departure_airport)
                    seg.departure_lat = dep_info.get("lat")
                    seg.departure_lon = dep_info.get("lon")
                    
                    seg.arrival_airport_name = arr_info.get("name", seg.arrival_airport)
                    seg.arrival_lat = arr_info.get("lat")
                    seg.arrival_lon = arr_info.get("lon")

        return final_flights

flight_service = FlightService()