from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from app.core.enums import BookingStatus, BookingType

class BookingBase(BaseModel):
    booking_type: BookingType
    confirmation_code: Optional[str] = None
    end_date: Optional[datetime] = None
    event_id: Optional[int] = None
    notes: Optional[str] = None
    provider_name: str
    start_date: datetime
    status: BookingStatus = BookingStatus.PENDING
    total_price: float
    trip_id: Optional[int] = None

class BookingCreate(BookingBase):
    pass

class BookingResponse(BookingBase):
    id: int
    user_id: int

    class Config:
        from_attributes = True