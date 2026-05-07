from pydantic import BaseModel
from typing import Optional

class Attraction(BaseModel):
    id: int
    name: str
    category: str         
    attraction_type: str  
    address: str          
    website: Optional[str] = None
    opening_hours: Optional[str] = None
    latitude: float   
    longitude: float  