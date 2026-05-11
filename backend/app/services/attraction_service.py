from app.providers.base import ProviderFallbackManager
from app.providers.attractions.geoapify_provider import GeoapifyAttractionProvider

class AttractionService:
    def __init__(self):
        # Geoapify is primary. You can add a secondary provider (like Google Places or Amadeus) later!
        self.providers = [GeoapifyAttractionProvider()]

    async def get_attractions(self, lat: float, lon: float, radius_miles: int = 30):
        return await ProviderFallbackManager.execute(
            self.providers,
            "get_attractions",
            lat, lon, radius_miles
        )

attraction_service = AttractionService()