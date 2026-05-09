from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.db.database import get_db
from app.schemas.event import EventCreate, EventResponse
from app.services.event_service import event_service
from app.core.enums import EventCategory

router = APIRouter()

@router.post("/", response_model=EventResponse)
def create_event(
    event_in: EventCreate, 
    db: Session = Depends(get_db)
    # Optional: current_user = Depends(get_current_admin)
):
    """Create a new categorized event."""
    return event_service.create_event(db=db, event_in=event_in)


@router.get("/", response_model=List[EventResponse])
def get_events(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    destination_id: Optional[int] = None,
    category: Optional[EventCategory] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    db: Session = Depends(get_db)
):
    """
    Search and filter events.
    Supports filtering by specific destination, event category, and date ranges.
    """
    events = event_service.get_events(
        db=db, 
        skip=skip, 
        limit=limit, 
        destination_id=destination_id, 
        category=category,
        start_date=start_date, 
        end_date=end_date
    )
    return events