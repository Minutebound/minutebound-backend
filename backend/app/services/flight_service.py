from app.providers.base import ProviderFallbackManager
from app.providers.flights.serp_provider import SerpFlightProvider
from app.providers.flights.amadeus_provider import AmadeusFlightProvider

class FlightService:
    def __init__(self):
        # Amadeus is Primary, Serp is Fallback
        self.providers = [ AmadeusFlightProvider(),SerpFlightProvider()]

    async def search_flights(self, origin: str, destination: str, date: str, return_date: str, adults: int, travel_class: str = "ECONOMY", children: int = 0):
        return await ProviderFallbackManager.execute(
            self.providers,
            "search_flights",
            origin, destination, date, return_date, adults, travel_class, children
        )

flight_service = FlightService()