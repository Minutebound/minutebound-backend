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
):
    """Create a new categorized event."""
    return event_service.create_event(db=db, event_in=event_in)


@router.get("/top", response_model=List[EventResponse])
def get_top_events(
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db)
):
    """
    Fetch top events for the Landing Page carousel safely using event_service.
    """
    events = event_service.get_events(db=db, skip=0, limit=limit)
    return events


@router.get("/search", response_model=List[EventResponse])
def search_events(
    category: Optional[str] = None, 
    query: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Search endpoint powering the /events Explorer map.
    Safely maps the string 'category' to your EventCategory Enum.
    """
    enum_category = None
    if category and category.lower() != "all":
        try:
            # Convert string to your Enum type
            enum_category = EventCategory(category)
        except ValueError:
            pass # Ignore invalid categories and just return all

    # Fetch events using your existing service
    events = event_service.get_events(db=db, skip=0, limit=1000, category=enum_category)
    
    # Apply text search filter safely in Python
    if query:
        search_term = query.lower()
        events = [
            e for e in events 
            if (e.title and search_term in e.title.lower()) or 
               (e.venue_name and search_term in e.venue_name.lower())
        ]
        
    return events


@router.get("/{event_id}", response_model=EventResponse)
def get_event(
    event_id: int, 
    db: Session = Depends(get_db)
):
    """
    Fetch a single event's full details by ID.
    """
    # Most services use get_event or get, adjust this method name if your service uses a different one
    event = event_service.get_event(db=db, event_id=event_id)
    if not event:
        raise HTTPException(status_code=404, detail="Event not found")
    return event


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
    Standard list and filter events.
    """
    return event_service.get_events(
        db=db, 
        skip=skip, 
        limit=limit, 
        destination_id=destination_id, 
        category=category,
        start_date=start_date, 
        end_date=end_date
    )