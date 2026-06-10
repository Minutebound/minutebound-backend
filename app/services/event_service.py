from sqlalchemy.orm import Session
from datetime import datetime
from app.db.models import Event
from app.schemas.event import EventCreate
from app.core.enums import EventCategory

class EventService:
    def create_event(self, db: Session, event_in: EventCreate) -> Event:
        db_event = Event(**event_in.model_dump())
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        return db_event

    def get_events(
        self, db: Session, skip: int = 0, limit: int = 50, 
        destination_id: int = None, category: EventCategory = None,
        start_date: datetime = None, end_date: datetime = None
    ):
        query = db.query(Event)
        
        if destination_id:
            query = query.filter(Event.destination_id == destination_id)
        if category:
            query = query.filter(Event.category == category)
        if start_date:
            query = query.filter(Event.start_time >= start_date)
        if end_date:
            query = query.filter(Event.start_time <= end_date)
            
        return query.order_by(Event.start_time.asc()).offset(skip).limit(limit).all()

event_service = EventService()