from fastapi import APIRouter, HTTPException, Query
from app.services.weather_service import weather_service
from app.schemas.weather import WeatherSummary
from fastapi_cache.decorator import cache
from datetime import date

router = APIRouter()

@router.get("/forecast", response_model=WeatherSummary)
@cache(expire=None) 
async def get_trip_weather(
    lat: float = Query(..., ge= -90, le= 90, description="Latitude must be between -90 and 90"),
    lon: float = Query(..., ge= -180, le= 180, description="Longitude must be between -180 and 180"),
    check_in_date: date = Query(...),
    check_out_date: date = Query(...)
):
    """
    Fetches the weather for the specific dates of the trip.
    If dates are > 30 days away, automatically extracts the City ID and uses Historical Data from exactly 1 year ago.
    """
    result = await weather_service.get_weather_for_trip(
        lat=lat, lon=lon, 
        check_in_date=str(check_in_date), check_out_date=str(check_out_date)
    )
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result