from app.providers.base import ProviderFallbackManager
from app.providers.flights.serp_provider import SerpFlightProvider
from app.providers.flights.amadeus_provider import AmadeusFlightProvider

class FlightService:
    def __init__(self):
        # Amadeus is Primary, Serp is Fallback
        self.amadeus_provider = AmadeusFlightProvider()
        self.serp_provider = SerpFlightProvider()
        self.providers = [self.amadeus_provider, self.serp_provider]  # order of fallback

    async def search_flights(self, origin: str, destination: str, date: str, return_date: str, adults: int, travel_class: str = "ECONOMY", children: int = 0):
        return await ProviderFallbackManager.execute(
            self.providers,
            "search_flights",
            origin, destination, date, return_date, adults, travel_class, children
        )

    async def confirm_price(self, flight_offer: dict):
        """Directs pricing requests exclusively to Amadeus"""
        return await self.amadeus_provider.confirm_price_and_policies(flight_offer)
        
    async def book_flight(self, priced_offer: dict, travelers: list):
        """Directs booking requests exclusively to Amadeus"""
        return await self.amadeus_provider.book_flight(priced_offer, travelers)

flight_service = FlightService()