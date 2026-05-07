from fastapi import APIRouter, HTTPException, Query
from typing import List
from app.services.attraction_service import attraction_service
from app.schemas.attraction import Attraction
from fastapi_cache.decorator import cache

router = APIRouter()

@router.get("/nearby", response_model=List[Attraction])
@cache(expire=None)
async def get_nearby_attractions(
    lat: float = Query(..., description="Destination Latitude from global state"),
    lon: float = Query(..., description="Destination Longitude from global state"),
    radius_miles: int = Query(30, description="Search radius in miles")
):
    """
    Fetches attractions from OpenStreetMap categorized into Amenities, Leisure, Historic, and Tourism.
    Results are dynamically grouped by category and sorted alphabetically.
    """
    result = await attraction_service.get_attractions(lat=lat, lon=lon, radius_miles=radius_miles)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result