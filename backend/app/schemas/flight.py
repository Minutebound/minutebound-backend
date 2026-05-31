from pydantic import BaseModel
from typing import List, Optional, Dict, Any

class Amenities(BaseModel):
    legroom: Optional[str] = None
    wifi: Optional[bool] = False
    power_usb: Optional[bool] = False
    food: Optional[str] = None

class BaggageAllowance(BaseModel):
    type: str  # "checked" or "carry_on"
    quantity: int

class RefundPolicy(BaseModel):
    is_refundable: bool
    penalty_amount: Optional[float] = None
    currency: Optional[str] = None

class FlightSegment(BaseModel):
    departure_airport: str
    departure_airport_name: Optional[str] = None  
    departure_terminal: Optional[str] = None
    departure_time: str
    
    arrival_airport: str
    arrival_airport_name: Optional[str] = None    
    arrival_terminal: Optional[str] = None
    arrival_time: str
    
    carrier_code: str
    carrier_name: str
    flight_number: str
    aircraft: Optional[str] = None
    duration: Optional[str] = None
    cabin_class: Optional[str] = None
    
    # Updated for Duffel
    baggages: List[BaggageAllowance] = []
    amenities: Optional[Amenities] = None

class FlightItinerary(BaseModel):
    duration: str
    stops: int
    segments: List[FlightSegment]

class FlightOffer(BaseModel):
    id: str  # Duffel Offer ID
    price: float
    currency: str
    airline_code: str
    airline_name: str
    cabin_class: str
    carbon_emissions_kg: Optional[int] = None
    itineraries: List[FlightItinerary]
    refund_policy: Optional[RefundPolicy] = None
    raw_offer_data: Optional[Dict[str, Any]] = None

class PriceConfirmResponse(BaseModel):
    priced_offer: FlightOffer
    seat_maps: Optional[List[Dict[str, Any]]] = None # Pass Duffel seatmaps to frontend

class PriceConfirmRequest(BaseModel):
    offer_id: str  # Updated from flight_offer: dict

class FlightBookRequest(BaseModel):
    offer_id: str  # Updated from priced_offer: dict
    travelers: list
    selected_seats: Optional[list] = None

class PaymentIntentRequest(BaseModel):
    amount: float
    currency: str = "USD"
    capture_method: Optional[str] = "manual" # Required for Hold & Capture flow

class ImportOrderRequest(BaseModel):
    order_id: str