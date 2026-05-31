from app.providers.flights.duffel_provider import DuffelFlightProvider

class FlightService:
    def __init__(self):
        self.duffel_provider = DuffelFlightProvider()

    async def get_flights(self, origin: str, destination: str, date: str, return_date: str = None, adults: int = 1, children: int = 0, travel_class: str = "ECONOMY"):
        return await self.duffel_provider.get_flights(
            origin=origin,
            destination=destination,
            date=date,
            return_date=return_date,
            adults=adults,
            children=children,
            travel_class=travel_class
        )

    async def confirm_price(self, offer_id: str):
        print(f"Checking live pricing for Duffel Offer: {offer_id}")
        result = await self.duffel_provider.confirm_price_and_policies(offer_id)
        
        # Log the exact error if Duffel rejects the pricing check (e.g., Expired)
        if isinstance(result, dict) and "error" in result:
            print(f"🚨 DUFFEL PRICING REJECTED: {result['error']}")
            
        return result

    async def book_flight(self, offer_id: str, travelers: list, selected_seats: list = None):
        return await self.duffel_provider.book_flight(
            offer_id=offer_id,
            travelers=travelers,
            selected_seats=selected_seats
        )

flight_service = FlightService()