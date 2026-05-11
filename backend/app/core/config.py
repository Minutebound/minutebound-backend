import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List

class Settings(BaseSettings):
    """Application Settings"""
    PROJECT_NAME: str = "Big Data Travel Planner"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    SECRET_KEY: str
    FRONTEND_URL: str 
    BACKEND_CORS_ORIGINS: List[str]
    POSTGRES_URL: str 

    # External APIs
    AMADEUS_CLIENT_ID: str 
    AMADEUS_CLIENT_SECRET: str 
    OPENWEATHER_API_KEY: str 
    BDC_API_KEY: str  
    DUFFEL_API_KEY: str
    
    SMTP_SERVER: str = "smtp.gmail.com" 
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = "" 
    SMTP_PASSWORD: str = "" 
    FROM_EMAIL: str = ""    
    OPENAI_API_KEY: str = ""

    MAPBOX_API_KEY: str = "" 
    SERPAPI_KEY: str = "" 
    AIRLABS_API_KEY: str = ""
    GEOAPIFY_API_KEY: str = "" # NEW

    model_config = SettingsConfigDict(
        env_file=".env.backend", 
        env_file_encoding="utf-8", 
        case_sensitive=True,
        extra="ignore" 
    )

settings = Settings()