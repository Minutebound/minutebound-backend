import pytest
from unittest.mock import patch, AsyncMock
import app.api.v1.endpoints.weather as weather
from datetime import date 
from dateutil.relativedelta import relativedelta

pytestmark = pytest.mark.asyncio

@pytest.mark.regression
class Test_Weather():
    api_path = "/api/v1/weather/forecast"
    today = date.today()
    check_in_date = str(today + relativedelta(days=1))
    check_out_date = str(today + relativedelta(days=2))

    default_params = {
        "lat": 10,
        "lon": 10,
        "check_in_date": check_in_date,
        "check_out_date": check_out_date
    }

    # @pytest.mark.skip(reason= "reduce api testing calls during development")
    async def test_pass(self, client):
        response = client.get(self.api_path, params= self.default_params)

        assert response.status_code == 200
        assert bool(response.json()) # Check that json is not empty

    # @pytest.mark.skip(reason= "reduce api testing calls during development")
    async def test_boundary_coordinates(self, client):
        response = client.get(self.api_path, params= self.default_params)

        assert response.status_code == 200
        assert bool(response.json()) # Check that json is not empty

    # @pytest.mark.skip(reason= "reduce api testing calls during development")
    async def test_same_day(self, client):
        tomorrow = str(self.today + relativedelta(days= 1))

        response = client.get(
            self.api_path, 
            params= {
                **self.default_params, 
                "check_in_date": tomorrow, 
                "check_out_date": tomorrow
            }
        )

        assert response.status_code == 200
        assert bool(response.json()) # Check that json is not empty


    # @pytest.mark.skip(reason= "reduce api testing calls during development")
    async def test_forecast_after_30_days(self, client):
        check_in_date_two_months_ahead = date.today() + relativedelta(months= 2)
        check_out_date_two_months_ahead = check_in_date_two_months_ahead + relativedelta(days= 1)

        response = client.get(
            self.api_path, 
            params= {
                **self.default_params, 
                "check_in_date": check_in_date_two_months_ahead, 
                "check_out_date": check_out_date_two_months_ahead
            }
        )

        assert response.status_code == 200
        
        data = response.json()
        assert "overall_summary" in data
        assert "days" in data
        assert len(data["days"]) > 0

    

    # @pytest.mark.skip(reason= "reduce api testing calls during development")
    async def test_bad_latitude(self, client):
        response = client.get(
            self.api_path, 
            params= {**self.default_params, "lat": 999}
        )

        assert response.status_code == 422

    # @pytest.mark.skip(reason= "reduce api testing calls during development")
    async def test_bad_longitude(self, client):
        response = client.get(
            self.api_path, 
            params= {**self.default_params, "lon": 999}
        )

        assert response.status_code == 422

    # @pytest.mark.skip(reason= "reduce api testing calls during development")
    async def test_invalid_date(self, client):
        """
        Test invalid date using invalid leap year.
        """
        invalid_leap_year_2026 = "2026-02-29"

        response = client.get(
            self.api_path, 
            params= {
                **self.default_params, 
                "check_in_date": invalid_leap_year_2026, 
                "check_out_date": invalid_leap_year_2026
            }
        )

        assert response.status_code == 422

    # @pytest.mark.skip(reason= "reduce api testing calls during development")
    async def test_get_trip_weather_missing_params(self, client):
        response = client.get(self.api_path, params = {"lat":10})

        assert response.status_code == 422

    # @pytest.mark.skip(reason= "reduce api testing calls during development")
    async def test_past_dates(self, client):
        check_in_date_2000 = "2000-01-01"
        check_out_date_2000 = "2000-01-02"
        response = client.get(
            self.api_path, 
            params= {
                **self.default_params, 
                "check_in_date": check_in_date_2000, 
                "check_out_date": check_out_date_2000
            }
        )

        assert response.status_code == 400
        assert response.json()['detail'] == "Cannot request weather for dates in the past"

    # @pytest.mark.skip(reason= "reduce api testing calls during development")
    async def test_check_out_date_before_check_in(self, client):
        check_in_date_swap = self.check_out_date
        check_out_date_swap = self.check_in_date

        response = client.get(
            self.api_path, 
            params= {
                **self.default_params, 
                "check_in_date": check_in_date_swap, 
                "check_out_date": check_out_date_swap
            }
        )

        assert response.status_code == 400
        assert response.json()['detail'] == "Invalid date format (end, start)"
    
    # @pytest.mark.skip(reason= "mocked test")
    # @patch('app.api.v1.endpoints.weather.weather_service.get_weather_for_trip', new_callable=AsyncMock)
    # async def test_get_trip_weather_bad_latitude(self, mock_get_weather_for_trip, client):
    #     mock_get_weather_for_trip.return_value = {"detail": "Failed to fetch data from OpenWeather"}

    #     response = client.get(
    #         self.api_path,
    #         params = {
    #             "lat": 999,
    #             "lon": 10,
    #             "check_in_date": "2026-04-10",
    #             "check_out_date": "2026-04-17"
    #         }
    #     )

    #     assert response.status_code == 400
    #     assert response.json()['detail'] == "Failed to fetch data from OpenWeather"
    