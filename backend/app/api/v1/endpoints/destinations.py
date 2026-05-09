from fastapi import APIRouter, Request, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.db.database import get_db
from app.schemas.destination import DestinationCreate, DestinationResponse
from app.services.destination_service import destination_service
from app.core.enums import PlaceType
from app.api.v1.deps import get_current_admin

router = APIRouter()

@router.get("/top")
async def get_top_destinations(request: Request):
    """Returns the top 5 most searched destinations using Redis."""
    try:
        top_destinations = await request.app.state.redis.zrevrange("top_destinations", 0, 4, withscores=True)
        
        results = []
        for dest, count in top_destinations:
            parts = dest.split(", ")
            city = parts[0]
            state = parts[1] if len(parts) > 1 else ""
            
            results.append({
                "city": city,
                "state": state,
                "full_name": dest,
                "searches": int(count)
            })
            
        return results
    except Exception as e:
        print(f"[Redis] Failed to fetch top destinations: {e}")
        return []

# --- NEW DATABASE ENDPOINTS ---

@router.post("/", response_model=DestinationResponse)
def create_destination(
    dest_in: DestinationCreate, 
    db: Session = Depends(get_db),
    # Optional: protect this route so only admins can add places
    # current_user = Depends(get_current_admin)
):
    """Create a new destination in the database."""
    return destination_service.create_destination(db=db, dest_in=dest_in)


@router.get("/search", response_model=List[DestinationResponse])
def search_destinations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    state_code: Optional[str] = None,
    place_type: Optional[PlaceType] = None,
    db: Session = Depends(get_db)
):
    """Search for destinations by state or OSM place type (city, town, county, etc)."""
    return destination_service.search_destinations(
        db=db, skip=skip, limit=limit, state_code=state_code, place_type=place_type
    )


@router.get("/{dest_id}", response_model=DestinationResponse)
def get_destination(dest_id: int, db: Session = Depends(get_db)):
    """Fetch a specific destination by its ID."""
    dest = destination_service.get_destination(db=db, dest_id=dest_id)
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")
    return dest