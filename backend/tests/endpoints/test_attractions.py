import pytest
from unittest.mock import patch, AsyncMock
from app.api.v1.endpoints.attractions import *
from app.schemas.attraction import Attraction

pytestmark = pytest.mark.asyncio

@pytest.mark.regression
class TestAttractions():
    api_path = '/api/v1/attractions/nearby'

    default_params = {
        "lat": 40.7128,
        "lon": -74.0060,
        "radius_miles": 30,
    }

    # --- Live endpoint call: valid coordinate sets ---
    nearby_attractions_param = ("lat, lon, radius_miles",
                        [
                            pytest.param(40.7128, -74.0060, 30, id="nyc"),
                            pytest.param(34.0522, -118.2437, 30, id="la"),
                            pytest.param(41.8781, -87.6298, 30, id="chicago"),
                            pytest.param(39.7392, -104.9903, None, id="denver_default_radius"),
                        ])

    @pytest.mark.parametrize(*nearby_attractions_param)
    async def test_get_nearby_attractions(self, client, lat, lon, radius_miles):
        params = {"lat": lat, "lon": lon}
        if radius_miles is not None:
            params["radius_miles"] = radius_miles

        response = client.get(self.api_path, params=params)

        if response.status_code == 400:
            pytest.skip(f"Upstream API error: {response.json().get('detail')}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            try:
                Attraction(**data[0])
            except Exception as e:
                pytest.fail(f"Attraction object creation error: {e}")

    # --- Validation / 422 error cases ---
    validation_error_param = ("params",
                        [
                            pytest.param({"lon": -74.0060}, id="missing_lat"),
                            pytest.param({"lat": 40.7128}, id="missing_lon"),
                            pytest.param({}, id="missing_all_params"),
                            pytest.param({"lat": "not-a-number", "lon": -74.0060}, id="invalid_lat_type"),
                            pytest.param({"lat": 40.7128, "lon": -74.0060, "radius_miles": "not-a-number"}, id="invalid_radius_type"),
                        ])

    @pytest.mark.parametrize(*validation_error_param)
    async def test_validation_errors(self, client, params):
        response = client.get(self.api_path, params=params)
        assert response.status_code == 422

    # --- Mocked service responses ---
    service_response_param = ("service_return, expected_status, expected_body",
                        [
                            pytest.param({"error": "External API failed"}, 400, {"detail": "External API failed"}, id="service_error"),
                            pytest.param([], 200, [], id="empty_result"),
                        ])

    @pytest.mark.parametrize(*service_response_param)
    async def test_service_responses(self, client, service_return, expected_status, expected_body):
        with patch(
            'app.api.v1.endpoints.attractions.attraction_service.get_attractions',
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = service_return

            response = client.get(self.api_path, params=self.default_params)

            assert response.status_code == expected_status
            assert response.json() == expected_body
