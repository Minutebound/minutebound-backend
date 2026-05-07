from fastapi import APIRouter, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.v1.deps import get_current_user
from app.db.models import User, UserEvent
from app.schemas.analytics import EventBatchRequest
from typing import Optional

router = APIRouter()

def process_events_background(events_data: EventBatchRequest, user_id: Optional[str], db: Session):
    new_events = []
    for evt in events_data.events:
        new_events.append(
            UserEvent(
                session_id=events_data.session_id,
                user_id=user_id,
                event_category=evt.event_category,
                event_action=evt.event_action,
                event_metadata=evt.event_metadata,
                page_url=evt.page_url,
                created_at=evt.timestamp
            )
        )
    db.add_all(new_events)
    db.commit()

@router.post("/track")
async def track_events(
    request: EventBatchRequest, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db),
    # Use Depends but don't strictly require a token if you track guests. 
    # Adjust this based on your auth structure.
    current_user: Optional[User] = Depends(get_current_user) 
):
    background_tasks.add_task(
        process_events_background, 
        events_data=request, 
        user_id=current_user.id if current_user else None, 
        db=db
    )
    return {"status": "accepted"}