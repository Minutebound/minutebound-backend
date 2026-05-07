from pydantic import BaseModel, Field
from typing import Dict, Any, Optional, List
from datetime import datetime
from uuid import UUID

class EventCreate(BaseModel):
    event_category: str = Field(..., max_length=50, description="e.g., TRIP_SEARCH")
    event_action: str = Field(..., max_length=100, description="e.g., INITIATED_SEARCH")
    event_metadata: Dict[str, Any] = Field(default_factory=dict, description="Custom JSON payload")
    page_url: Optional[str] = None
    timestamp: Optional[datetime] = None # Allows frontend to send exact time the click happened

class EventBatchRequest(BaseModel):
    session_id: Optional[UUID] = None
    events: List[EventCreate]