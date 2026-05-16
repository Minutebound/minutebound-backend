import httpx
import asyncio
import airportsdata
from app.core.config import settings
from app.schemas.flight import FlightOffer, FlightSegment, FlightItinerary, Amenities

class SerpFlightProvider:
    # ... __init__ stays the same ...

    def _parse_flight_data(self, raw_data: dict, expected_class: str) -> list[FlightOffer]:
        clean_results = []
        raw_flights = raw_data.get("best_flights", []) + raw_data.get("other_flights", [])

        for idx, offer in enumerate(raw_flights):
            try:
                price = float(offer.get("price", 0.0))
                if price == 0.0: continue

                segments_data = offer.get("flights", [])
                if not segments_data: continue

                clean_segments = []
                for seg in segments_data:
                    dep = seg.get("departure_airport", {})
                    arr = seg.get("arrival_airport", {})
                    airline_name = seg.get("airline", "UNKNOWN")

                    duration_mins = seg.get("duration", 0)
                    seg_duration = f"{duration_mins // 60}H {duration_mins % 60}M" if duration_mins else "N/A"

                    # Parse amenities from Google's extensions
                    amenities = Amenities(legroom=seg.get("legroom"))
                    for ext in seg.get("extensions", []):
                        ext_low = ext.lower()
                        if "wi-fi" in ext_low or "wifi" in ext_low: amenities.wifi = True
                        if "power" in ext_low or "usb" in ext_low: amenities.power_usb = True
                        if "meal" in ext_low or "snack" in ext_low: amenities.food = ext

                    clean_segments.append(FlightSegment(
                        departure_airport=dep.get("id", "TBA"),
                        departure_time=dep.get("time", "TBA"),
                        arrival_airport=arr.get("id", "TBA"),
                        arrival_time=arr.get("time", "TBA"),
                        carrier_code=airline_name, 
                        carrier_name=airline_name,  
                        flight_number=str(seg.get("flight_number", "TBA")),
                        aircraft=seg.get("airplane"),
                        duration=seg_duration,
                        cabin_class=seg.get("travel_class", expected_class),
                        amenities=amenities
                    ))

                duration_mins = offer.get("total_duration", 0)
                formatted_duration = f"{duration_mins // 60}H {duration_mins % 60}M" if duration_mins else "N/A"
                emissions = offer.get("carbon_emissions", {}).get("this_flight") # Extracts emissions in grams

                clean_results.append(FlightOffer(
                    id=f"serpapi_leg_{idx}", 
                    price=price,
                    currency="USD",
                    airline_code=clean_segments[0].carrier_name if clean_segments else "UNKNOWN",
                    airline_name=clean_segments[0].carrier_name if clean_segments else "UNKNOWN",    
                    cabin_class=expected_class,
                    carbon_emissions_kg=(emissions // 1000) if emissions else None,
                    itineraries=[FlightItinerary(duration=formatted_duration, stops=max(0, len(clean_segments) - 1), segments=clean_segments)] 
                ))
            except Exception:
                continue
        return clean_results

    async def get_flights(self, origin: str, destination: str, date: str, return_date: str, adults: int, travel_class: str = "ECONOMY", children: int = 0):
        if not self.api_key: return {"error": "SerpApi Key missing"}

        classes_to_search = [c.strip().upper() for c in travel_class.split(",")]
        travel_class_map = {"ECONOMY": "1", "PREMIUM_ECONOMY": "2", "BUSINESS": "3", "FIRST": "4"}
        
        async def fetch_for_class(t_class):
            mapped_class = travel_class_map.get(t_class, "1")
            base_params = {"engine": "google_flights", "currency": "USD", "hl": "en", "adults": adults, "travel_class": mapped_class, "api_key": self.api_key, "type": "2"}
            if children > 0: base_params["children"] = children

            async with httpx.AsyncClient() as client:
                outbound_params = {**base_params, "departure_id": origin, "arrival_id": destination, "outbound_date": date}
                requests = [client.get(self.base_url, params=outbound_params, timeout=30.0)]
                
                if return_date:
                    requests.append(client.get(self.base_url, params={**base_params, "departure_id": destination, "arrival_id": origin, "outbound_date": return_date}, timeout=30.0))

                responses = await asyncio.gather(*requests, return_exceptions=True)
                
                outbound_offers = self._parse_flight_data(responses[0].json(), t_class) if not isinstance(responses[0], Exception) and responses[0].status_code == 200 else []

                if return_date and len(responses) == 2:
                    return_offers = self._parse_flight_data(responses[1].json(), t_class) if not isinstance(responses[1], Exception) and responses[1].status_code == 200 else []
                    combined = []
                    for outb, inb in zip(outbound_offers, return_offers):
                        outb.price += inb.price 
                        outb.itineraries.extend(inb.itineraries) 
                        combined.append(outb)
                    return combined
                return outbound_offers

        tasks = [fetch_for_class(c) for c in classes_to_search]
        class_results = await asyncio.gather(*tasks)

        final_flights = []
        for res_list in class_results:
            if isinstance(res_list, list): final_flights.extend(res_list)

        if not final_flights:
            return {"error": "No flights found via SerpApi"}

        return final_flights