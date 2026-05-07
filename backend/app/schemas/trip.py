from pydantic import BaseModel
from typing import List, Optional, Any, Dict

class TripGenerateRequest(BaseModel):
    username: str
    destination: str
    check_in_date: str
    check_out_date: str
    
    email: Optional[str] = None 
    drive: Optional[Dict[str, Any]] = None 
    
    flight: Optional[Dict[str, Any]] = None
    hotel: Optional[Dict[str, Any]] = None
    weather: Optional[Dict[str, Any]] = None
    activities: Optional[List[Dict[str, Any]]] = []
    attractions: Optional[List[Dict[str, Any]]] = []