from fastapi import APIRouter, Query, HTTPException
from datetime import date
from typing import Optional
import httpx
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/forecast")
async def get_weather_forecast(
    # Explicitly matching the exact parameters sent by the frontend
    lat: float = Query(..., description="Latitude"),
    lon: float = Query(..., description="Longitude"),
    start_date: Optional[date] = Query(None, description="Start date of the trip"),
    end_date: Optional[date] = Query(None, description="End date of the trip")
):
    """
    Fetches weather data for the given coordinates and dates.
    Accepts lat, lon, start_date, and end_date to prevent 422 errors.
    """
    try:
        # We use Open-Meteo for free, no-auth weather data
        weather_url = "https://api.open-meteo.com/v1/forecast"
        
        # Open-meteo parameters
        params = {
            "latitude": lat,
            "longitude": lon,
            "daily": "weather_code,temperature_2m_max,temperature_2m_min",
            "temperature_unit": "fahrenheit",
            "timezone": "auto"
        }

        # If dates are provided, fetch for that specific window
        if start_date and end_date:
            params["start_date"] = start_date.isoformat()
            params["end_date"] = end_date.isoformat()

        async with httpx.AsyncClient() as client:
            response = await client.get(weather_url, params=params)
            response.raise_for_status()
            data = response.json()

        # WMO Weather interpretation codes (WMO code 4677)
        weather_codes = {
            0: "Clear skies",
            1: "Mainly clear", 2: "Partly cloudy", 3: "Overcast",
            45: "Fog", 48: "Depositing rime fog",
            51: "Light drizzle", 53: "Moderate drizzle", 55: "Dense drizzle",
            61: "Light rain", 63: "Moderate rain", 65: "Heavy rain",
            71: "Light snow", 73: "Moderate snow", 75: "Heavy snow",
            95: "Thunderstorm", 96: "Thunderstorm with light hail", 99: "Thunderstorm with heavy hail"
        }

        # Structure the response EXACTLY how your frontend ItineraryModal expects it
        days = []
        if "daily" in data:
            daily = data["daily"]
            for i in range(len(daily.get("time", []))):
                code = daily["weather_code"][i]
                days.append({
                    "date": daily["time"][i],
                    "max_temp": daily["temperature_2m_max"][i],
                    "min_temp": daily["temperature_2m_min"][i],
                    "weather": weather_codes.get(code, "Unknown conditions")
                })

        # Calculate a mock ideal month based on hemisphere/latitude if needed, 
        # or default to a pleasant string.
        ideal_month = "September" if lat > 0 else "March"

        return {
            "days": days,
            "ideal_month": ideal_month,
            "current": {
                "temp_f": days[0]["max_temp"] if days else 72,
                "condition": {"text": days[0]["weather"]} if days else {"text": "Clear skies"}
            }
        }

    except httpx.HTTPStatusError as e:
        logger.error(f"Weather API HTTP error: {e}")
        raise HTTPException(status_code=502, detail="Failed to fetch weather from provider")
    except Exception as e:
        logger.error(f"Unexpected weather error: {e}")
        raise HTTPException(status_code=500, detail="Internal server error while fetching weather")