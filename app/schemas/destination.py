from pydantic import BaseModel
from typing import Optional, List

class DestinationBase(BaseModel):
    name: str
    latitude: float
    longitude: float
    place_name: Optional[str] = None
    state_code: Optional[str] = None
    category: Optional[str] = None # Mountain Retreats, City Breaks, etc.
    description: Optional[str] = None
    image_url: Optional[str] = None
    avg_flight_price: Optional[float] = None
    avg_hotel_price: Optional[float] = None

class DestinationCreate(DestinationBase):
    pass

class DestinationResponse(DestinationBase):
    id: int
    popularity_score: int

    class Config:
        from_attributes = True