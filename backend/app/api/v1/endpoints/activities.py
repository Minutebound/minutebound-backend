from fastapi import APIRouter, HTTPException, Query
from typing import List
from app.services.activity_service import activity_service
from app.schemas.activity import Activity
from fastapi_cache.decorator import cache

router = APIRouter()

@router.get("/nearby", response_model=List[Activity])
@cache(expire=None)
async def get_nearby_activities(
    lat: float = Query(..., description="Destination Latitude from global state"),
    lon: float = Query(..., description="Destination Longitude from global state"),
    radius_miles: int = Query(30, description="Search radius in miles (default 30)")
):
    """
    Fetches activities, tours, and experiences near the destination.
    Returns name, price, picture, and minimum duration sorted by distance.
    """
    result = await activity_service.get_activities_nearby(lat=lat, lon=lon, radius_miles=radius_miles)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result