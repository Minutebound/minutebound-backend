from pydantic import BaseModel
from typing import Optional, Dict, Any, List

class Hotel(BaseModel):
    chain_code: Optional[str] = None
    iata_code: Optional[str] = None
    hotel_id: str
    name: str
    geo_code: Optional[Dict[str, float]] = None
    rating: Optional[int] = None
    distance_km: Optional[float] = None
    address: Optional[Dict[str, Any]] = None 

class RoomOffer(BaseModel):
    room_name: str
    description: Optional[str] = None
    category: Optional[str] = None
    bed_type: Optional[str] = None
    beds_count: Optional[int] = None
    price: float
    currency: str
    amenities: List[str]

class HotelOffer(BaseModel):
    hotel_id: str
    name: Optional[str] = None
    check_in_date: str
    check_out_date: str
    guests: int
    price: float
    currency: str
    address: Optional[Dict[str, Any]] = None
    latitude: Optional[float] = None   
    longitude: Optional[float] = None
    rooms: Optional[List[RoomOffer]] = []