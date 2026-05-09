from pydantic import BaseModel
from typing import Optional
from app.core.enums import PlaceType

class DestinationBase(BaseModel):
    name: str
    osm_id: Optional[str] = None
    place_type: PlaceType
    latitude: float
    longitude: float
    state_code: Optional[str] = None
    county: Optional[str] = None
    country_code: str = "US"
    population: Optional[int] = None
    description: Optional[str] = None
    image_url: Optional[str] = None

class DestinationCreate(DestinationBase):
    pass

class DestinationResponse(DestinationBase):
    id: int

    class Config:
        from_attributes = True