from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
from enum import Enum as PyEnum

class VisibilityEnum(str, PyEnum):
    PRIVATE = "PRIVATE"
    PUBLIC = "PUBLIC"

class ItineraryGenerateRequest(BaseModel):
    username: str
    destination: str
    check_in_date: str
    check_out_date: str
    
    email: Optional[str] = None 
    drive: Optional[Dict[str, Any]] = None 
    
    flight: Optional[Dict[str, Any]] = None
    hotel: Optional[Dict[str, Any]] = None
    weather: Optional[Dict[str, Any]] = None
    tours: Optional[List[Dict[str, Any]]] = []
    attractions: Optional[List[Dict[str, Any]]] = []

class ItineraryBase(BaseModel):
    destination: str
    data: Dict[str, Any]
    visibility: VisibilityEnum = VisibilityEnum.PRIVATE

class ItineraryCreate(ItineraryBase):
    pass

class ItineraryUpdate(BaseModel):
    destination: Optional[str] = None
    data: Optional[Dict[str, Any]] = None
    visibility: Optional[VisibilityEnum] = None

class ItineraryResponse(ItineraryBase):
    id: str
    user_id: str
    share_token: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class UpdateVisibilityRequest(BaseModel):
    visibility: VisibilityEnum

class ShareItineraryEmailRequest(BaseModel):
    email: EmailStr
    message: Optional[str] = Field(None, max_length=500, description="Optional personal message to include in the email")