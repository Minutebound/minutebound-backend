import pytest
from unittest.mock import patch, AsyncMock
from datetime import date as date_module
from dateutil.relativedelta import relativedelta
from app.api.v1.endpoints.hotels import *
from app.schemas.hotel import Hotel, HotelOffer

pytestmark = pytest.mark.asyncio


def _future_dates(months=1, stay_days=3):
    check_in = date_module.today() + relativedelta(months=months)
    check_out = check_in + relativedelta(days=stay_days)
    return str(check_in), str(check_out)


@pytest.mark.regression
class TestHotelsNearby():
    api_path = "/api/v1/hotels/nearby"

    @property
    def default_params(self):
        check_in, check_out = _future_dates()
        return {
            "lat": 40.7128,
            "lon": -74.0060,
            "check_in_date": check_in,
            "check_out_date": check_out,
            "adults": 2,
            "radius": 50,
        }

    # --- Live endpoint call ---
    nearby_hotels_param = ("lat, lon, adults, radius",
                        [
                            pytest.param(40.7128, -74.0060, 2, 50, id="nyc"),
                            pytest.param(34.0522, -118.2437, 1, 50, id="la_solo"),
                            pytest.param(41.8781, -87.6298, 4, 20, id="chicago_family"),
                        ])

    @pytest.mark.parametrize(*nearby_hotels_param)
    async def test_get_nearby_hotels(self, client, lat, lon, adults, radius):
        check_in, check_out = _future_dates()
        response = client.get(
            self.api_path,
            params={
                "lat": lat,
                "lon": lon,
                "check_in_date": check_in,
                "check_out_date": check_out,
                "adults": adults,
                "radius": radius,
            },
        )

        if response.status_code == 400:
            pytest.skip(f"Upstream API error: {response.json().get('detail')}")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        if data:
            try:
                Hotel(**data[0])
            except Exception as e:
                pytest.fail(f"Hotel object creation error: {e}")

    # --- Validation errors ---
    validation_error_param = ("overrides",
                        [
                            pytest.param({"lat": None}, id="missing_lat"),
                            pytest.param({"lon": None}, id="missing_lon"),
                            pytest.param({"check_in_date": None}, id="missing_check_in"),
                            pytest.param({"adults": None}, id="missing_adults"),
                            pytest.param({"lat": "not-a-number"}, id="invalid_lat_type"),
                            pytest.param({"adults": "not-a-number"}, id="invalid_adults_type"),
                        ])

    @pytest.mark.parametrize(*validation_error_param)
    async def test_validation_errors(self, client, overrides):
        params = dict(self.default_params)
        for k, v in overrides.items():
            if v is None:
                params.pop(k, None)
            else:
                params[k] = v

        response = client.get(self.api_path, params=params)
        assert response.status_code == 422

    # --- Mocked service responses ---
    service_response_param = ("service_return, expected_status, expected_body",
                        [
                            pytest.param({"error": "Amadeus API failed"}, 400, {"detail": "Amadeus API failed"}, id="service_error"),
                            pytest.param([], 200, [], id="empty_result"),
                        ])

    @pytest.mark.parametrize(*service_response_param)
    async def test_service_responses(self, client, service_return, expected_status, expected_body):
        with patch(
            "app.api.v1.endpoints.hotels.hotel_service.get_available_hotels_by_geocode",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = service_return

            response = client.get(self.api_path, params=self.default_params)

            assert response.status_code == expected_status
            assert response.json() == expected_body


@pytest.mark.regression
class TestHotelOffer():
    api_path = "/api/v1/hotels/offer"

    @property
    def default_params(self):
        check_in, check_out = _future_dates()
        return {
            "hotel_id": "HTLNYC001",
            "check_in_date": check_in,
            "check_out_date": check_out,
            "adults": 2,
        }

    # --- Validation errors ---
    offer_validation_param = ("overrides",
                        [
                            pytest.param({"hotel_id": None}, id="missing_hotel_id"),
                            pytest.param({"check_in_date": None}, id="missing_check_in"),
                            pytest.param({"adults": None}, id="missing_adults"),
                            pytest.param({"adults": "not-a-number"}, id="invalid_adults_type"),
                        ])

    @pytest.mark.parametrize(*offer_validation_param)
    async def test_validation_errors(self, client, overrides):
        params = dict(self.default_params)
        for k, v in overrides.items():
            if v is None:
                params.pop(k, None)
            else:
                params[k] = v

        response = client.get(self.api_path, params=params)
        assert response.status_code == 422

    # --- Mocked service responses ---
    offer_service_param = ("service_return, expected_status, expected_detail",
                        [
                            pytest.param({"error": "Hotel offer not available"}, 400, "Hotel offer not available", id="service_error"),
                            pytest.param({"error": "Invalid hotel id"}, 400, "Invalid hotel id", id="invalid_hotel_id"),
                        ])

    @pytest.mark.parametrize(*offer_service_param)
    async def test_service_error_responses(self, client, service_return, expected_status, expected_detail):
        with patch(
            "app.api.v1.endpoints.hotels.hotel_service.get_specific_hotel_offer",
            new_callable=AsyncMock,
        ) as mock_get:
            mock_get.return_value = service_return

            response = client.get(self.api_path, params=self.default_params)

            assert response.status_code == expected_status
            assert response.json()["detail"] == expected_detail
