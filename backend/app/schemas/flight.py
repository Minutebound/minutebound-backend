from pydantic import BaseModel
from typing import List, Optional

class FlightSegment(BaseModel):
    departure_airport: str
    departure_airport_name: Optional[str] = None  
    departure_lat: Optional[float] = None
    departure_lon: Optional[float] = None
    departure_time: str
    
    arrival_airport: str
    arrival_airport_name: Optional[str] = None    
    arrival_lat: Optional[float] = None
    arrival_lon: Optional[float] = None
    arrival_time: str
    
    carrier_code: str
    carrier_name: str
    flight_number: str
    checked_bags: Optional[int] = 0  

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