from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.core.enums import EventCategory

class EventBase(BaseModel):
    title: str
    description: Optional[str] = None
    category: EventCategory
    start_time: datetime
    end_time: Optional[datetime] = None
    destination_id: int
    address: Optional[str] = None
    venue_name: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    price_min: Optional[float] = None
    price_max: Optional[float] = None
    ticket_url: Optional[str] = None
    image_url: Optional[str] = None

class EventCreate(EventBase):
    pass

class EventResponse(EventBase):
    id: int

    class Config:
        from_attributes = True