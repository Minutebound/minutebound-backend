from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional, Any

from app.db.database import get_db
from app.schemas.destination import DestinationCreate, DestinationResponse
from app.services.destination_service import destination_service

router = APIRouter()

@router.get("/", response_model=List[DestinationResponse])
def get_destinations(
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """
    Standard list endpoint for destinations.
    Includes pagination (skip/limit) for efficient data loading.
    """
    # If you have a destination_service.py, you can route this through it
    # return destination_service.get_destinations(db=db, skip=skip, limit=limit)
    
    # Otherwise, direct SQLAlchemy query:
    return db.query(Destination).offset(skip).limit(limit).all()

@router.get("/top")
async def get_top_destinations(db: Session = Depends(get_db)):
    """Returns top manual destinations and live SerpApi trending locations."""
    return await destination_service.get_top_destinations(db)

@router.post("/", response_model=DestinationResponse)
def create_destination(dest_in: DestinationCreate, db: Session = Depends(get_db)):
    """Create a new manual destination."""
    return destination_service.create_destination(db=db, dest_in=dest_in)

@router.get("/search", response_model=List[DestinationResponse])
def search_destinations(
    query: Optional[str] = None,
    state_code: Optional[str] = None,
    category: Optional[str] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db)
):
    """Search destinations by name, state, or category (e.g. Hidden Gems)."""
    return destination_service.search_destinations(
        db=db, query=query, state_code=state_code, category=category, skip=skip, limit=limit
    )

@router.get("/{dest_id}", response_model=DestinationResponse)
def get_destination(dest_id: int, db: Session = Depends(get_db)):
    """Fetch a specific destination by its ID."""
    dest = destination_service.get_destination(db=db, dest_id=dest_id)
    if not dest:
        raise HTTPException(status_code=404, detail="Destination not found")
    return dest
