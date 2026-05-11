from app.providers.base import ProviderFallbackManager
from app.providers.stays.serp_provider import SerpStayProvider
from app.providers.stays.amadeus_provider import AmadeusStayProvider

class StayService:
    def __init__(self):
        # Amadeus is Primary, Serp is Fallback
        self.providers = [AmadeusStayProvider(),SerpStayProvider()]

    async def get_available_hotels_by_geocode(self, lat: float, lon: float, check_in_date: str, check_out_date: str, adults: int, radius: int = 50):
        return await ProviderFallbackManager.execute(
            self.providers,
            "get_available_hotels_by_geocode",
            lat, lon, check_in_date, check_out_date, adults, radius
        )

    async def get_specific_hotel_offer(self, hotel_id: str, check_in_date: str, check_out_date: str, adults: int):
        return await ProviderFallbackManager.execute(
            self.providers,
            "get_specific_hotel_offer",
            hotel_id, check_in_date, check_out_date, adults
        )

stay_service = StayService()