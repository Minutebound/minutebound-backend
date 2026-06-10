import pytest
from unittest.mock import patch, AsyncMock
from app.api.v1.endpoints.driving import *

pytestmark = pytest.mark.asyncio

@pytest.mark.regression
class TestDriving():
    api_path = "/api/v1/driving/route"

    default_params = {
        "origin_lat": 40.7128,
        "origin_lon": -74.0060,
        "dest_lat": 42.3601,
        "dest_lon": -71.0589,
    }

    # --- Live endpoint call ---
    route_param = ("origin_lat, origin_lon, dest_lat, dest_lon",
                        [
                            pytest.param(40.7128, -74.0060, 42.3601, -71.0589, id="nyc_to_boston"),
                            pytest.param(34.0522, -118.2437, 36.1699, -115.1398, id="la_to_vegas"),
                            pytest.param(39.7392, -104.9903, 40.0150, -105.2705, id="denver_to_boulder"),
                        ])

    @pytest.mark.parametrize(*route_param)
    async def test_get_driving_route(self, client, origin_lat, origin_lon, dest_lat, dest_lon):
        response = client.get(
            self.api_path,
            params={
                "origin_lat": origin_lat,
                "origin_lon": origin_lon,
                "dest_lat": dest_lat,
                "dest_lon": dest_lon,
            },
        )

        if response.status_code >= 500:
            pytest.skip(f"Upstream error: {response.text}")
        assert response.status_code == 200
        assert isinstance(response.json(), dict)

    # --- Validation errors ---
    validation_error_param = ("params",
                        [
                            pytest.param({}, id="missing_all_params"),
                            pytest.param({"origin_lat": 40.7, "origin_lon": -74.0, "dest_lat": 42.3}, id="missing_dest_lon"),
                            pytest.param({**default_params, "origin_lat": "not-a-number"}, id="invalid_origin_lat_type"),
                            pytest.param({**default_params, "dest_lon": "not-a-number"}, id="invalid_dest_lon_type"),
                        ])

    @pytest.mark.parametrize(*validation_error_param)
    async def test_validation_errors(self, client, params):
        response = client.get(self.api_path, params=params)
        assert response.status_code == 422

    # --- Mocked service responses ---
    service_response_param = ("service_return",
                        [
                            pytest.param({"distance_km": 346, "duration_min": 215, "polyline": "abc"}, id="normal_route"),
                            pytest.param({"error": "No route found"}, id="service_error_payload"),
                            pytest.param({}, id="empty_dict"),
                        ])

    @pytest.mark.parametrize(*service_response_param)
    async def test_service_responses(self, client, service_return):
        with patch(
            "app.services.driving_service.DrivingService.get_route",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = service_return

            response = client.get(self.api_path, params=self.default_params)

            assert response.status_code == 200
            assert response.json() == service_return
