from pydantic import BaseModel
from typing import Optional, Dict

class Location(BaseModel):
    id: Optional[str] = None
    name: str
    detailed_name: Optional[str] = None
    iata_code: Optional[str] = None
    
    # --- ALIGNED WITH DESTINATION SCHEMA ---
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    state_code: Optional[str] = None
    country_code: Optional[str] = "US"
    
    # For external API (like Amadeus) strictly 
    # requires or returns raw nested dicts and you want to preserve them.
    geo_code: Optional[Dict[str, float]] = None 
    address: Optional[Dict[str, str]] = None