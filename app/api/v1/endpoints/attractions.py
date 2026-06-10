from fastapi import APIRouter, HTTPException, Query
from app.services.attraction_service import attraction_service
from fastapi_cache.decorator import cache

router = APIRouter()

@router.get("/nearby")
@cache(expire=86400) # Cache for 24 hours to save API calls
async def get_nearby_attractions(
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    radius_miles: int = Query(30, description="Search radius in miles")
):
    result = await attraction_service.get_attractions(lat=lat, lon=lon, radius_miles=radius_miles)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result