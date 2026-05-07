import pytest
from unittest.mock import patch, AsyncMock
import app.api.v1.endpoints.activities as activities

pytestmark = pytest.mark.asyncio

@pytest.mark.regression
class TestActivities():
    api_path = '/api/v1/activities/nearby'

    default_params = {
        "lat": 40.7128,
        "lon": -74.0060,
        "radius_miles": 30
    }

    # @pytest.mark.skip(reason= "reduce api testing calls during development")
    async def test_pass(self, client):
        response = client.get(self.api_path, params=self.default_params)

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    # @pytest.mark.skip(reason= "reduce api testing calls during development")
    async def test_default_radius(self, client):
        response = client.get(
            self.api_path,
            params={"lat": 40.7128, "lon": -74.0060}
        )

        assert response.status_code == 200
        assert isinstance(response.json(), list)

    # @pytest.mark.skip(reason= "reduce api testing calls during development")
    async def test_missing_lat(self, client):
        response = client.get(
            self.api_path,
            params={"lon": -74.0060}
        )

        assert response.status_code == 422

    # @pytest.mark.skip(reason= "reduce api testing calls during development")
    async def test_missing_lon(self, client):
        response = client.get(
            self.api_path,
            params={"lat": 40.7128}
        )

        assert response.status_code == 422

    # @pytest.mark.skip(reason= "reduce api testing calls during development")
    async def test_missing_all_params(self, client):
        response = client.get(self.api_path)

        assert response.status_code == 422

    # @pytest.mark.skip(reason= "reduce api testing calls during development")
    async def test_invalid_lat_type(self, client):
        response = client.get(
            self.api_path,
            params={**self.default_params, "lat": "not-a-number"}
        )

        assert response.status_code == 422

    # @pytest.mark.skip(reason= "reduce api testing calls during development")
    async def test_invalid_radius_type(self, client):
        response = client.get(
            self.api_path,
            params={**self.default_params, "radius_miles": "not-a-number"}
        )

        assert response.status_code == 422

    @patch('app.api.v1.endpoints.activities.activity_service.get_activities_nearby', new_callable=AsyncMock)
    async def test_service_error(self, mock_get_activities, client):
        mock_get_activities.return_value = {"error": "External API failed"}

        response = client.get(self.api_path, params=self.default_params)

        assert response.status_code == 400
        assert response.json()["detail"] == "External API failed"

    @patch('app.api.v1.endpoints.activities.activity_service.get_activities_nearby', new_callable=AsyncMock)
    async def test_empty_result(self, mock_get_activities, client):
        mock_get_activities.return_value = []

        response = client.get(self.api_path, params=self.default_params)

        assert response.status_code == 200
        assert response.json() == []
