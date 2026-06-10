from app.providers.base import ProviderFallbackManager
from app.providers.routing.mapbox_provider import MapboxRoutingProvider
from app.providers.routing.geoapify_provider import GeoapifyRoutingProvider

class DrivingService:
    def __init__(self):
        self.providers = [MapboxRoutingProvider(), GeoapifyRoutingProvider()]

    async def get_route(self, origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float):
        return await ProviderFallbackManager.execute(
            self.providers,
            "get_route",
            origin_lat, origin_lon, dest_lat, dest_lon
        )

driving_service = DrivingService()