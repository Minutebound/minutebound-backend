from app.providers.base import ProviderFallbackManager
from app.providers.tours.amadeus_provider import AmadeusTourProvider

class TourService:
    def __init__(self):
        self.providers = [AmadeusTourProvider()]

    async def get_tours_nearby(self, lat: float, lon: float, radius_miles: int = 30):
        return await ProviderFallbackManager.execute(
            self.providers,
            "get_tours_nearby",
            lat, lon, radius_miles
        )

tour_service = TourService()