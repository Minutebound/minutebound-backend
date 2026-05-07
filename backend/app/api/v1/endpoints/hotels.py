from fastapi import APIRouter, HTTPException, Query
from typing import List
from app.services.hotel_service import hotel_service
from app.schemas.hotel import Hotel, HotelOffer
from fastapi_cache.decorator import cache

router = APIRouter()

@router.get("/nearby", response_model=List[Hotel])
@cache(expire=None) 
async def get_nearby_hotels(
    lat: float = Query(..., description="Destination Latitude from global state"),
    lon: float = Query(..., description="Destination Longitude from global state"),
    check_in_date: str = Query(..., description="Arrival Date YYYY-MM-DD"),
    check_out_date: str = Query(..., description="Departure Date YYYY-MM-DD"),
    adults: int = Query(..., description="Number of adults"),
    radius: int = Query(50, description="Search radius in KM")
):
    """
    Step 1: Fetches a list of hotels near the destination that ACTUALLY have rooms available.
    """
    result = await hotel_service.get_available_hotels_by_geocode(
        lat=lat, lon=lon, 
        check_in_date=check_in_date, check_out_date=check_out_date, 
        adults=adults, radius=radius
    )
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

@router.get("/offer", response_model=HotelOffer)
@cache(expire=86400) 
async def get_hotel_price(
    hotel_id: str = Query(..., description="The Amadeus Hotel ID from the clicked checkbox"),
    check_in_date: str = Query(..., description="Arrival Date YYYY-MM-DD"),
    check_out_date: str = Query(..., description="Departure Date YYYY-MM-DD"),
    adults: int = Query(..., description="Number of adults")
):
    """
    Step 2: Returns the price when the checkbox is clicked (Instantly pulled from cache).
    """
    result = await hotel_service.get_specific_hotel_offer(
        hotel_id=hotel_id, 
        check_in_date=check_in_date, 
        check_out_date=check_out_date, 
        adults=adults
    )
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result