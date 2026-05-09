from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_active_user, get_current_super_admin
from app.core.enums import UserRole
from app.db.database import get_db
from app.db.models import User
from app.schemas.booking import BookingCreate, BookingResponse
from app.services.booking_service import booking_service

router = APIRouter()

@router.post("/", response_model=BookingResponse)
def create_booking(
    booking_in: BookingCreate,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Authenticated User: Create a new booking for themselves."""
    return booking_service.create_booking(booking_in=booking_in, db=db, user_id=current_user.id)

@router.get("/", response_model=List[BookingResponse])
def get_all_bookings(
    current_admin: User = Depends(get_current_super_admin),
    db: Session = Depends(get_db),
    limit: int = 100,
    skip: int = 0
):
    """Super Admin only: Retrieve all bookings across the entire site."""
    return booking_service.get_all_bookings(db=db, limit=limit, skip=skip)

@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
):
    """Retrieve a specific booking by ID. Accessible by the owner or a Super Admin."""
    booking = booking_service.get_booking_by_id(booking_id=booking_id, db=db)
    
    if not booking:
        raise HTTPException(detail="Booking not found", status_code=404)
        
    if booking.user_id != current_user.id and current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(detail="Not enough permissions to view this booking", status_code=403)
        
    return booking

@router.get("/me/list", response_model=List[BookingResponse])
def get_my_bookings(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db),
    limit: int = 100,
    skip: int = 0
):
    """Authenticated User: Retrieve their own personal bookings."""
    return booking_service.get_user_bookings(db=db, limit=limit, skip=skip, user_id=current_user.id)