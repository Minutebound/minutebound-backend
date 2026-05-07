import json
import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from app.api.v1.endpoints.locations import * 
from app.api.v1.endpoints.flights import * 
from pydantic import BaseModel
from typing import List
from datetime import date as date_module
from dateutil.relativedelta import relativedelta

class FlightSegment(BaseModel):
    departure_airport: str
    departure_time: str
    arrival_airport: str
    arrival_time: str
    carrier_code: str
    carrier_name: str
    flight_number: str

class FlightItinerary(BaseModel):
    duration: str
    stops: int
    segments: List[FlightSegment]

class FlightOffer(BaseModel):
    id: str
    price: float
    currency: str
    airline_code: str
    airline_name: str
    cabin_class: str
    itineraries: List[FlightItinerary]

@pytest.mark.regression
class Testapiendpoints():

    get_airport_endpoint_param = ("lat, long, expected_output",
                            [
                                # DENVER Positive test
                                pytest.param(39.7392, -104.9903, {"iata": "DEN"}, id="denver"),
                                # JFK Positive test
                                pytest.param(40.6413, -73.7781, {"iata": "JFK"}, id="jfk"),
                                # LAX Positive test
                                pytest.param(33.9416, -118.4085, {"iata": "LAX"}, id="lax"),
                                # Ocean / no nearby airport
                                pytest.param(0.0, 0.0, {"iata": None}, id="middle_of_ocean"),
                                # Antarctica / no nearby airport
                                pytest.param(-85.0, 0.0, {"iata": None}, id="antarctica"),
                            ])


    search_flight_endpoint_param = ("origin, destination, date, return_date, adults, travel_class, children, expected_output",
                            [
                                # DEN -> JFK Positive test (dates dynamically generated below via a fixture in the test)
                                pytest.param("DEN", "JFK", None, None, 2, "ECONOMY", 0, FlightOffer, id="den_to_jfk_economy"),
                                # DEN -> LAX with business class
                                pytest.param("DEN", "LAX", None, None, 1, "BUSINESS", 0, FlightOffer, id="den_to_lax_business"),
                                # With children
                                pytest.param("DEN", "JFK", None, None, 2, "ECONOMY", 2, FlightOffer, id="den_to_jfk_with_children"),
                            ])

    @pytest.mark.parametrize(*get_airport_endpoint_param)
    @pytest.mark.anyio
    async def test_get_nearest_airport(self, lat, long, expected_output):
        """ Hitting actual endpoint. Need Api Keys and internet connection for this test. """
        airport = await get_nearest_airport(lat, long)
        assert airport == expected_output


    @pytest.mark.parametrize(*search_flight_endpoint_param)
    @pytest.mark.anyio
    async def test_search_flights(self, origin, destination, date, return_date, adults, travel_class, children, expected_output):
        # Use dynamic dates ~1 month out so tests don't break as time passes
        if date is None:
            date = str(date_module.today() + relativedelta(months=1))
        if return_date is None:
            return_date = str(date_module.today() + relativedelta(months=1, days=5))

        flights = await search_flights(origin, destination, date, return_date, adults, travel_class, children)

        assert isinstance(flights, list)
        if len(flights) == 0:
            pytest.skip("No flights returned from live API for this route/class")

        first = flights[0]
        data = first.model_dump() if hasattr(first, "model_dump") else (first.dict() if hasattr(first, "dict") else first)
        try:
            expected_output(**data)
        except Exception as e:
            pytest.fail(f"Flight object creation error: {e}")


    # --- Mocked error cases (no real API calls) ---

    search_flight_error_param = ("origin, destination, service_return, expected_status",
                            [
                                # Same origin and destination
                                pytest.param("DEN", "DEN", {"error": "Origin and destination cannot be the same"}, 400, id="same_origin_destination"),
                                # Service failure
                                pytest.param("DEN", "JFK", {"error": "Amadeus API failed"}, 400, id="service_failure"),
                                # Invalid IATA code
                                pytest.param("XXX", "JFK", {"error": "Invalid origin airport code"}, 400, id="invalid_origin_iata"),
                            ])

    @pytest.mark.parametrize(*search_flight_error_param)
    @pytest.mark.anyio
    async def test_search_flights_errors(self, origin, destination, service_return, expected_status):
        date = str(date_module.today() + relativedelta(months=1))
        return_date = str(date_module.today() + relativedelta(months=1, days=5))

        with patch("app.api.v1.endpoints.flights.flight_service.search_flights", new_callable=AsyncMock) as mock_search:
            mock_search.return_value = service_return

            with pytest.raises(HTTPException) as exc_info:
                await search_flights(origin, destination, date, return_date, 1, "ECONOMY", 0)

            assert exc_info.value.status_code == expected_status
            assert exc_info.value.detail == service_return["error"]
        
        
    # mock = AsyncMock()
    
    # @pytest.mark.parametrize(*search_flight_endpoint_param)
    # @pytest.mark.anyio
    # async def test_search_flights_with_mock(self, origin, destination, date, return_date, adults, travel_class, children, expected_output):
    #     self.mock.return_value = expected_output
    #     with patch("backend.app.api.v1.endpoints.flights.flight_service.search_flights") as mock_api:
    #         flights = await search_flights(origin, destination, date, return_date, adults, travel_class, children)
    #         print(flights[0])
    #         assert isinstance(flights[0], expected_output)
    
    # @pytest.mark.parametrize(*get_airport_endpoint_param)
    # @pytest.mark.anyio
    # async def test_get_nearest_airport_mock(self, lat, long, expected_output):
    #     """
    #         Testing with no api access. Testing general functionality of function
    #     """
    #    
    #     mock.return_value = expected_output
    #     with patch("backend.app.api.v1.endpoints.locations.location_service.get_airports_by_location", mock) as api_mock:
    #         airport = await get_nearest_airport(lat, long)
    #         assert airport == expected_output
    
