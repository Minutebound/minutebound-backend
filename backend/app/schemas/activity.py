from pydantic import BaseModel
from typing import Optional, Dict

class Activity(BaseModel):
    id: str
    name: str
    short_description: Optional[str] = None
    geo_code: Optional[Dict[str, float]] = None
    price: Optional[float] = None
    currency: Optional[str] = None
    picture_url: Optional[str] = None
    minimum_duration: Optional[str] = None
    distance_km: Optional[float] = None  