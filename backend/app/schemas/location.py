from pydantic import BaseModel
from typing import Optional, Dict

class Location(BaseModel):
    id: Optional[str] = None
    name: str
    detailed_name: Optional[str] = None
    iata_code: str
    geo_code: Optional[Dict[str, float]] = None 
    address: Optional[Dict[str, str]] = None