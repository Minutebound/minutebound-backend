import os
import httpx
from datetime import datetime
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.api.v1.deps import get_current_user, get_current_admin
from app.core.enums import UserRole, BookingType, BookingStatus
from app.db.database import get_db
from app.db.models import User, Booking
from app.schemas.booking import BookingCreate, BookingResponse
from app.services.booking_service import booking_service

router = APIRouter()

@router.post("/", response_model=BookingResponse)
def create_booking(
    booking_in: BookingCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Authenticated User: Create a new booking for themselves."""
    return booking_service.create_booking(booking_in=booking_in, db=db, user_id=current_user.id)

@router.get("/", response_model=List[BookingResponse])
def get_all_bookings(
    current_admin: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
    limit: int = 100,
    skip: int = 0
):
    """Super Admin only: Retrieve all bookings across the entire site."""
    return booking_service.get_all_bookings(db=db, limit=limit, skip=skip)

@router.get("/{booking_id}", response_model=BookingResponse)
def get_booking(
    booking_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve a specific booking by ID. Accessible by the owner or a Super Admin."""
    booking = booking_service.get_booking_by_id(booking_id=booking_id, db=db)
    
    if not booking:
        raise HTTPException(detail="Booking not found", status_code=404)
        
    if booking.user_id != current_user.id and current_user.role != UserRole.SUPER_ADMIN:
        raise HTTPException(detail="Not enough permissions to view this booking", status_code=403)
        
    return booking

@router.get("/me/bookings", response_model=List[BookingResponse])
def get_my_bookings(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    limit: int = 100,
    skip: int = 0
):
    """Authenticated User: Retrieve their own personal bookings."""
    # This maps perfectly to travelApi.getMyBookings() on your frontend
    return booking_service.get_user_bookings(db=db, limit=limit, skip=skip, user_id=current_user.id)

@router.get("/duffel-order/{order_id}")
async def get_live_duffel_order(
    order_id: str,
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    """
    Fetches the live order from Duffel AND auto-syncs it to the DB if missing.
    """
    try:
        token = os.getenv('DUFFEL_API_KEY')
        if not token:
            raise HTTPException(status_code=500, detail="Server config error: Missing Duffel Token")

        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {token}",
                "Duffel-Version": "v2", 
                "Content-Type": "application/json"
            }
            res = await client.get(f"https://api.duffel.com/air/orders/{order_id}", headers=headers)
            
            # Auto-fallback for Versioning
            if res.status_code == 400 and "version" in res.text.lower():
                headers["Duffel-Version"] = "beta"
                res = await client.get(f"https://api.duffel.com/air/orders/{order_id}", headers=headers)

            if res.status_code != 200:
                raise HTTPException(status_code=res.status_code, detail=f"Duffel Error: {res.text}")
                
            order_data = res.json().get("data", {})
            
            # --- DATABASE AUTO-SYNC ---
            try:
                # Check if we already have it to prevent duplicates
                existing = db.query(Booking).filter(Booking.notes.like(f"%{order_id}%")).first()
                if not existing:
                    print(f"🔄 Order {order_id} not found in DB. Auto-syncing now...")
                    
                    # Safe Extraction
                    try:
                        f_seg = order_data.get("slices", [{}])[0].get("segments", [{}])[0]
                        l_seg = order_data.get("slices", [{}])[-1].get("segments", [{}])[-1]
                        sync_start = datetime.fromisoformat(f_seg.get("departing_at", "").replace("Z", "+00:00"))
                        sync_end = datetime.fromisoformat(l_seg.get("arriving_at", "").replace("Z", "+00:00"))
                        airline = f_seg.get("operating_carrier", {}).get("name", "Unknown Airline")
                    except:
                        sync_start, sync_end, airline = datetime.utcnow(), datetime.utcnow(), "Unknown"

                    sync_booking = Booking(
                        user_id=current_user.id,
                        booking_type=BookingType.FLIGHT,
                        confirmation_code=order_data.get("booking_reference", ""),
                        notes=f"Duffel Order ID: {order_id}. Auto-Synced.",
                        provider_name="Duffel", 
                        airline_provider=airline, 
                        start_date=sync_start,
                        end_date=sync_end,
                        status=BookingStatus.CONFIRMED,
                        total_price=float(order_data.get("total_amount", 0.0))
                    )
                    db.add(sync_booking)
                    db.commit()
                    print(f"✅ Auto-sync complete for {order_id}!")
            except Exception as e:
                db.rollback()
                print(f"🚨 AUTO-SYNC FAILED: {str(e)}")

            return order_data
            
    except HTTPException: 
        raise
    except Exception as e: 
        # By wrapping the WHOLE block in a try/except, 
        # any missing imports or typos will be safely caught and returned as JSON instead of crashing the server!
        print(f"CRITICAL ERROR: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")