import httpx
from datetime import datetime, timedelta, timezone
from collections import defaultdict, Counter
from app.schemas.weather import WeatherDay, WeatherSummary
from app.core.config import settings  

class WeatherService:
    def __init__(self):
        self.api_key = settings.WEATHER_API_KEY

    async def get_weather_for_trip(self, lat: float, lon: float, check_in_date: str, check_out_date: str):
        check_in = datetime.strptime(check_in_date, "%Y-%m-%d")                                                                                                                                                             
        check_out = datetime.strptime(check_out_date, "%Y-%m-%d") 
        
        now = datetime.now()

        if check_in > check_out:
            return {'error': 'Invalid date format (end, start)', 'status_code': 400}
        
        if check_in.date() < now.date():
            return {'error': 'Cannot request weather for dates in the past', 'status_code': 400}

        print(f"🔍 [WEATHER] CACHE MISS: Fetching forecast for {lat}, {lon} from {check_in_date}")

        days_until_trip = (check_in - now).days

        forecast_url = "https://pro.openweathermap.org/data/2.5/forecast/climate"
        forecast_params = {
            "lat": lat, "lon": lon,
            "appid": self.api_key,
            "units": "imperial", 
            "cnt": 30
        }

        async with httpx.AsyncClient() as client:
            try:
                print(f"🌤️ Fetching Forecast for {lat}, {lon}")
                forecast_response = await client.get(forecast_url, params=forecast_params, timeout=15.0)
                if forecast_response.status_code != 200:
                    return {"error": "Failed to fetch data from OpenWeather.", "status_code": 400}
                
                forecast_data = forecast_response.json()
                
                tz_offset = forecast_data.get("city", {}).get("timezone", 0)

                if days_until_trip <= 30:
                    return self._parse_climate_data(forecast_data, check_in_date, check_out_date, tz_offset)

                print(f"🕰️ Trip is > 30 days away. Fetching historical data using exact coordinates: {lat}, {lon}")
                historical_check_in = check_in - timedelta(days=365)
                historical_check_out = check_out - timedelta(days=365)

                start_unix = int(historical_check_in.timestamp()) - 86400
                end_unix = int((historical_check_out + timedelta(days=1)).timestamp()) + 86400

                history_url = "https://history.openweathermap.org/data/2.5/history/city"
                history_params = {
                    "lat": lat,  
                    "lon": lon,
                    "type": "hour",
                    "start": start_unix,
                    "end": end_unix,
                    "appid": self.api_key,
                    "units": "imperial"
                }

                history_response = await client.get(history_url, params=history_params, timeout=15.0)
                if history_response.status_code == 200:
                    return self._parse_historical_data(history_response.json(), check_in_date, check_out_date, tz_offset)
                else:
                    return {"error": f"OpenWeather Historical API returned {history_response.status_code}: {history_response.text}"}
            except Exception as e:
                return {"error": f"Failed to fetch weather: {str(e)}"}

    def _parse_climate_data(self, data: dict, target_check_in: str, target_check_out: str, tz_offset: int):
        days = []
        check_in_dt = datetime.strptime(target_check_in, "%Y-%m-%d").date()
        check_out_dt = datetime.strptime(target_check_out, "%Y-%m-%d").date()

        for item in data.get("list", []):
            local_dt = datetime.fromtimestamp(item["dt"] + tz_offset, tz=timezone.utc).date()
            
            if check_in_dt <= local_dt <= check_out_dt:
                days.append(WeatherDay(
                    date=local_dt.strftime("%Y-%m-%d"),
                    max_temp=round(item["temp"]["max"], 1),
                    min_temp=round(item["temp"]["min"], 1),
                    weather=item["weather"][0]["description"].title(),
                    humidity=item["humidity"],
                    pressure=item["pressure"]
                ))

        if not days:
            return {"error": "Dates not found in 30-day forecast range."}

        all_weathers = [d.weather.lower() for d in days]
        most_common_overall = Counter(all_weathers).most_common(1)[0][0]
        avg_high = sum([d.max_temp for d in days]) / len(days)

        return WeatherSummary(
            overall_summary=f"Forecast for your trip: Expect mostly {most_common_overall} conditions with highs around {int(avg_high)}°F.",
            days=days
        )

    def _parse_historical_data(self, data: dict, target_check_in: str, target_check_out: str, tz_offset: int):
        daily_data = defaultdict(lambda: {"temps": [], "humidity": [], "pressure": [], "weather": []})

        for item in data.get("list", []):
            local_dt = datetime.fromtimestamp(item["dt"] + tz_offset, tz=timezone.utc)
            future_dt = local_dt + timedelta(days=365)
            date_str = future_dt.strftime("%Y-%m-%d")

            daily_data[date_str]["temps"].append(item["main"]["temp"])
            daily_data[date_str]["humidity"].append(item["main"]["humidity"])
            daily_data[date_str]["pressure"].append(item["main"]["pressure"])
            
            daily_data[date_str]["weather"].append(item["weather"][0]["main"])

        days = []
        for date_str, metrics in sorted(daily_data.items()):
            if target_check_in <= date_str <= target_check_out:
                most_common_weather = Counter(metrics["weather"]).most_common(1)[0][0]

                days.append(WeatherDay(
                    date=date_str,
                    max_temp=round(max(metrics["temps"]), 1),
                    min_temp=round(min(metrics["temps"]), 1),
                    weather=most_common_weather.title() + " (Historical Estimate)",
                    humidity=int(sum(metrics["humidity"]) / len(metrics["humidity"])),
                    pressure=int(sum(metrics["pressure"]) / len(metrics["pressure"]))
                ))

        if not days:
            return {"error": "Could not calculate historical forecast for these dates."}

        avg_high = sum([d.max_temp for d in days]) / len(days)

        return WeatherSummary(
            overall_summary=f"ℹ️ Prediction based on historical data: Expect mostly {days[0].weather.split(' ')[0].lower()} conditions with highs around {int(avg_high)}°F.",
            days=days
        )

weather_service = WeatherService()