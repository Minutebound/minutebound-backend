from pydantic import BaseModel
from typing import Optional

class Attraction(BaseModel):
    id: str
    name: str
    category: Optional[str] = None
    lat: float
    lon: float
    distance_km: Optional[float] = None
    address: Optional[str] = None