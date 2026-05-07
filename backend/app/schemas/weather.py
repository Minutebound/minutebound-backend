from pydantic import BaseModel
from typing import List

class WeatherDay(BaseModel):
    date: str
    max_temp: float
    min_temp: float
    weather: str
    humidity: int
    pressure: int

class WeatherSummary(BaseModel):
    overall_summary: str
    days: List[WeatherDay]