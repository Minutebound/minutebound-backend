from fastapi import APIRouter, HTTPException, Query
from typing import List
from app.services.flight_service import flight_service
from app.schemas.flight import FlightOffer
from fastapi_cache.decorator import cache

router = APIRouter()

@router.get("/search", response_model=List[FlightOffer])
@cache(expire=86400) 
async def search_flights(
    origin: str = Query(..., description="Departure airport IATA code (e.g., JFK)"),
    destination: str = Query(..., description="Arrival airport IATA code (e.g., LHR)"),
    date: str = Query(..., description="Departure date YYYY-MM-DD"),
    return_date: str = Query(..., description="Return date YYYY-MM-DD"),
    adults: int = Query(..., description="Number of adult passengers"),
    travel_class: str = Query("ECONOMY,PREMIUM_ECONOMY", description="Comma-separated cabin classes"),
    children: int = Query(0, description="Number of children (Optional)")
):
    """
    Search for round-trip flights supporting multiple cabin classes concurrently.
    """

    result = await flight_service.search_flights(
        origin=origin,
        destination=destination,
        date=date,
        return_date=return_date,
        adults=adults,
        travel_class=travel_class,
        children=children
    )
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result