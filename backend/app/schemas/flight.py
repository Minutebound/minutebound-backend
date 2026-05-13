from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Amenities(BaseModel):
    legroom: Optional[str] = None
    wifi: Optional[bool] = False
    power_usb: Optional[bool] = False
    food: Optional[str] = None

class FlightSegment(BaseModel):
    departure_airport: str
    departure_airport_name: Optional[str] = None  
    departure_terminal: Optional[str] = None
    departure_lat: Optional[float] = None
    departure_lon: Optional[float] = None
    departure_time: str
    
    arrival_airport: str
    arrival_airport_name: Optional[str] = None    
    arrival_terminal: Optional[str] = None
    arrival_lat: Optional[float] = None
    arrival_lon: Optional[float] = None
    arrival_time: str
    
    carrier_code: str
    carrier_name: str
    flight_number: str
    aircraft: Optional[str] = None
    duration: Optional[str] = None
    cabin_class: Optional[str] = None
    checked_bags: Optional[int] = 0  
    carry_on_bags: Optional[int] = 0
    amenities: Optional[Amenities] = None

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
    carbon_emissions_kg: Optional[int] = None
    itineraries: List[FlightItinerary]
    raw_offer_data: Optional[Dict[str, Any]] = None

class PriceConfirmRequest(BaseModel):
    """Payload to confirm the price of a specific flight offer"""
    flight_offer: Dict[str, Any]

class FlightBookRequest(BaseModel):
    """Payload to execute the actual booking"""
    priced_offer: Dict[str, Any]
    travelers: List[Dict[str, Any]]

class PaymentIntentRequest(BaseModel):
    amount: float
    currency: str = "USD"