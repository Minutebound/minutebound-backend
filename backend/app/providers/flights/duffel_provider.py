import os
import httpx
from typing import Dict, Any, List
from app.schemas.flight import (
    FlightOffer, FlightItinerary, FlightSegment, 
    BaggageAllowance, RefundPolicy
)

class DuffelFlightProvider:
    def __init__(self):
        # Your test key is pulled straight from the environment
        self.api_token = os.getenv("DUFFEL_API_KEY", "")
        self.base_url = "https://api.duffel.com"
        
        # Explicit V2 header per Duffel Documentation
        self.headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Duffel-Version": "v2", 
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    async def get_flights(self, origin: str, destination: str, date: str, return_date: str = None, adults: int = 1, travel_class: str = "ECONOMY", children: int = 0) -> List[FlightOffer]:
        try:
            # 1. Format Passengers (Duffel v2 requires explicit ages for children)
            passengers = [{"type": "adult"} for _ in range(adults)]
            if children > 0:
                passengers.extend([{"type": "child", "age": 8} for _ in range(children)])

            # 2. Format Slices (Force YYYY-MM-DD string)
            slices = [{"origin": origin, "destination": destination, "departure_date": date[:10]}]
            if return_date:
                slices.append({"origin": destination, "destination": origin, "departure_date": return_date[:10]})

            # 3. Construct Raw Payload
            payload = {
                "data": {
                    "slices": slices,
                    "passengers": passengers,
                    "cabin_class": travel_class.lower(),
                    "return_offers": True
                }
            }

            # 4. Make Request
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/air/offer_requests",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )
                
                if response.status_code not in [200, 201]:
                    print(f"\n🚨 DUFFEL SEARCH 400 ERROR: {response.text}\n")
                    return []

                # 5. Safely Parse Results
                data = response.json().get("data", {})
                offers = data.get("offers", [])

                formatted_offers = []
                for offer in offers:
                    try:
                        formatted_offers.append(self._format_offer(offer))
                    except Exception as e:
                        print(f"Skipped an offer due to parsing error: {e}")
                        
                return formatted_offers

        except Exception as e:
            print(f"🚨 DUFFEL REQUEST FAILED: {str(e)}") 
            return []

    async def confirm_price_and_policies(self, offer_id: str) -> Dict[str, Any]:
        """Fetches the updated price and seat maps using pure REST."""
        try:
            async with httpx.AsyncClient() as client:
                # 1. Re-fetch live offer
                offer_res = await client.get(
                    f"{self.base_url}/air/offers/{offer_id}?return_available_services=true",
                    headers=self.headers,
                    timeout=15.0
                )
                if offer_res.status_code != 200:
                    return {"error": f"Offer no longer available: {offer_res.text}"}
                
                offer_data = offer_res.json().get("data", {})

                # 2. Fetch Seat Maps
                seat_maps = []
                seat_res = await client.get(
                    f"{self.base_url}/air/seat_maps?offer_id={offer_id}",
                    headers=self.headers,
                    timeout=15.0
                )
                if seat_res.status_code == 200:
                    seat_maps = seat_res.json().get("data", [])

                return {
                    "priced_offer": self._format_offer(offer_data),
                    "seat_maps": seat_maps
                }
        except Exception as e:
            return {"error": f"Failed to confirm price: {str(e)}"}

    async def book_flight(self, offer_id: str, travelers: list, selected_seats: list = None) -> Dict[str, Any]:
        """Creates the Order using the Duffel Test Balance."""
        try:
            async with httpx.AsyncClient() as client:
                # 1. Fetch exact total amount required for the payment payload
                offer_res = await client.get(
                    f"{self.base_url}/air/offers/{offer_id}",
                    headers=self.headers
                )
                offer_data = offer_res.json().get("data", {})
                
                # 2. Format Passengers
                duffel_passengers = []
                for t in travelers:
                    phone = t["contact"]["phones"][0]
                    duffel_passengers.append({
                        "id": t["id"], 
                        "title": "mr" if str(t.get("gender")).upper() == "MALE" else "ms",
                        "given_name": t["name"]["firstName"],
                        "family_name": t["name"]["lastName"],
                        "born_on": t["dateOfBirth"][:10],
                        "email": t["contact"]["emailAddress"],
                        "phone_number": f"+{phone['countryCallingCode']}{phone['number']}",
                        "gender": "m" if str(t.get("gender")).upper() == "MALE" else "f"
                    })
                
                # 3. Format Addons
                services = [{"id": s["seatId"], "quantity": 1} for s in selected_seats] if selected_seats else []

                # 4. Construct Order Payload
                payload = {
                    "data": {
                        "type": "instant",
                        "selected_offers": [offer_id],
                        "passengers": duffel_passengers,
                        "payments": [{
                            "type": "balance",
                            "currency": offer_data.get("total_currency"),
                            "amount": offer_data.get("total_amount")
                        }]
                    }
                }
                if services:
                    payload["data"]["services"] = services

                # 5. Execute Booking
                order_res = await client.post(
                    f"{self.base_url}/air/orders",
                    headers=self.headers,
                    json=payload,
                    timeout=30.0
                )

                if order_res.status_code not in [200, 201]:
                    print(f"\n🚨 DUFFEL BOOKING ERROR: {order_res.text}\n")
                    return {"error": f"Booking failed: {order_res.text}"}

                order_data = order_res.json().get("data", {})
                return {
                    "success": True,
                    "booking_reference": order_data.get("booking_reference"), 
                    "order_id": order_data.get("id"),
                    "status": "confirmed"
                }

        except Exception as e:
            return {"error": f"Network error during booking: {str(e)}"}

    def _format_offer(self, offer: dict) -> FlightOffer:
        """Safely parses raw Duffel JSON dictionaries into our backend schema."""
        itineraries = []
        for slice_ in offer.get("slices", []):
            segments = []
            for seg in slice_.get("segments", []):
                
                # Extract Bags
                baggages = []
                for passenger in seg.get("passengers", []):
                    for baggage in passenger.get("baggages", []):
                        baggages.append(BaggageAllowance(
                            type=baggage.get("type", "checked"), 
                            quantity=baggage.get("quantity", 1)
                        ))

                aircraft = seg.get("aircraft")
                
                # Sometimes Duffel returns carrier info inside 'operating_carrier', sometimes it relies on the 'owner'
                owner = offer.get("owner", {})
                carrier = seg.get("operating_carrier") or owner

                segments.append(FlightSegment(
                    departure_airport=seg.get("origin", {}).get("iata_code", ""),
                    departure_airport_name=seg.get("origin", {}).get("name", ""),
                    departure_terminal=seg.get("origin_terminal"),
                    departure_time=seg.get("departing_at", ""),
                    arrival_airport=seg.get("destination", {}).get("iata_code", ""),
                    arrival_airport_name=seg.get("destination", {}).get("name", ""),
                    arrival_terminal=seg.get("destination_terminal"),
                    arrival_time=seg.get("arriving_at", ""),
                    carrier_code=carrier.get("iata_code", ""),
                    carrier_name=carrier.get("name", ""),
                    flight_number=seg.get("operating_carrier_flight_number", ""),
                    aircraft=aircraft.get("name") if aircraft else None,
                    duration=seg.get("duration"),
                    baggages=baggages
                ))
            
            itineraries.append(FlightItinerary(
                duration=slice_.get("duration", ""),
                stops=max(0, len(slice_.get("segments", [])) - 1),
                segments=segments
            ))

        # Extract Policies
        cond = offer.get("conditions", {}).get("refund_before_departure", {})
        is_refundable = cond.get("allowed", False)
        pen_amount = cond.get("penalty_amount")
        
        cabin_class = "economy"
        try:
            cabin_class = offer.get("slices")[0].get("segments")[0].get("passengers")[0].get("cabin_class", "economy")
        except:
            pass

        return FlightOffer(
            id=offer.get("id", ""),
            price=float(offer.get("total_amount", 0.0)),
            currency=offer.get("total_currency", "USD"),
            airline_code=offer.get("owner", {}).get("iata_code", ""),
            airline_name=offer.get("owner", {}).get("name", ""),
            cabin_class=cabin_class,
            carbon_emissions_kg=int(float(offer["total_emissions_kg"])) if offer.get("total_emissions_kg") else None,
            refund_policy=RefundPolicy(
                is_refundable=is_refundable,
                penalty_amount=float(pen_amount) if pen_amount is not None else None,
                currency=offer.get("base_currency") or offer.get("total_currency")
            ),
            itineraries=itineraries,
            raw_offer_data=offer 
        )
    
    async def get_live_offer_details(self, offer_id: str) -> Dict[str, Any]:
        """Helper to extract direct mapped schema payload before saving a row data entry."""
        async with httpx.AsyncClient() as client:
            res = await client.get(f"{self.base_url}/air/offers/{offer_id}", headers=self.headers)
            return self._format_offer(res.json().get("data", {}))

    async def get_order(self, order_id: str) -> dict:
        """Fetches the live order details directly from Duffel."""
        try:
            async with httpx.AsyncClient() as client:
                res = await client.get(
                    f"{self.base_url}/air/orders/{order_id}",
                    headers=self.headers,
                    timeout=15.0
                )
                if res.status_code == 200:
                    return res.json().get("data", {})
                return {"error": f"Order not found: {res.text}"}
        except Exception as e:
            return {"error": str(e)}
        
    async def get_order_details(self, order_id: str) -> Dict[str, Any]:
        """Retrieves raw order information to show detailed descriptions & simulate invoice lines."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/air/orders/{order_id}",
                headers=self.headers,
                timeout=15.0
            )
            if response.status_code != 200:
                return {"error": f"Failed to retrieve Duffel order info: {response.text}"}
            
            data = response.json().get("data", {})
            
            # Formulate structured receipt/invoice overview data block
            invoice_summary = {
                "invoice_number": f"INV-{data.get('id','').replace('ord_', '')}",
                "issued_at": data.get("created_at"),
                "payment_type": data.get("payments",[{}])[0].get("type", "balance"),
                "currency": data.get("total_currency"),
                "subtotal": float(data.get("base_amount", 0.0)),
                "taxes": float(data.get("tax_amount", 0.0)),
                "grand_total": float(data.get("total_amount", 0.0))
            }
            
            return {
                "raw_order": data,
                "invoice": invoice_summary
            }
        