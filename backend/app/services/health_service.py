import httpx
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import SystemHealthStatus
from app.db.database import SessionLocal 

# Detailed, human-readable definitions
HTTP_STATUS_DESCRIPTIONS = {
    200: "Successful Response - Service is Fully Operational",
    201: "Resource Created Successfully",
    202: "Request Accepted for Processing",
    204: "Request Processed Successfully (No Content Returned)", 
    400: "Bad Request - The server could not understand the request", 
    401: "Unauthorized - Missing or invalid API credentials", 
    403: "Forbidden - Access denied by the external provider", 
    404: "Not Found - The requested API endpoint does not exist", 
    405: "Method Not Allowed - Incorrect HTTP request type used", 
    406: "Not Acceptable - Requested format is not supported", 
    408: "Request Timeout - The provider took too long to respond", 
    422: "Unprocessable Entity - Request validation failed", 
    429: "Too Many Requests - Rate limit has been exceeded", 
    500: "Internal Server Error - Provider experienced a critical fault", 
    502: "Bad Gateway - Invalid response received from upstream provider", 
    503: "Service Unavailable - Provider is temporarily down for maintenance or overloaded", 
    504: "Gateway Timeout - Upstream provider failed to respond in time"
}

class HealthService:
    def __init__(self):
        self.cache_ttl = timedelta(hours=48)

    async def ping_endpoints(self, db: Session, target_api: str = None):
        """Pings both internal and external endpoints and saves all to the database schema."""
        print(f"🔄 [HEALTH] Pinging {'API: ' + target_api if target_api else 'all endpoints'}...")
        
        # Unified endpoint definitions (Internal + External)
        api_definitions = {
            "backend_api": {"url": "Internal Backend Service (Self-Check)", "method": "INTERNAL"},
            "frontend_app": {"url": str(settings.FRONTEND_URL), "method": "GET"},
            "OpenWeather": {"url": f"https://pro.openweathermap.org/data/2.5/weather?lat=0&lon=0&appid={settings.WEATHER_API_KEY or ''}", "method": "GET"},
            "SerpApi": {"url": f"https://serpapi.com/search.json?engine=google&q=test&api_key={settings.SERPAPI_KEY or ''}", "method": "GET"},
            "BigDataCloud": {"url": f"https://api-bdc.net/data/reverse-geocode?latitude=0&longitude=0&key={settings.BDC_API_KEY or ''}", "method": "GET"},
            "AirLabs": {"url": f"https://airlabs.co/api/v9/ping?api_key={settings.AIRLABS_API_KEY or ''}", "method": "GET"},
            "Amadeus_Auth": {"url": "https://api.amadeus.com/v1/security/oauth2/token", "method": "POST", "data": {"grant_type": "client_credentials", "client_id": settings.AMADEUS_CLIENT_ID or "", "client_secret": settings.AMADEUS_CLIENT_SECRET or ""}},
            "Amadeus_Tours": {"url": "https://api.amadeus.com/v1/shopping/activities?latitude=40.414369&longitude=-105.691708&radius=10", "method": "GET", "headers": {"Authorization": f"Bearer {settings.AMADEUS_CLIENT_ID or ''}"}},
            "OSM_Overpass": {"url": "https://lz4.overpass-api.de/api/interpreter", "method": "GET"},
            "Mapbox": {"url": f"https://api.mapbox.com/directions/v5/mapbox/driving/0,0;1,1?access_token={settings.MAPBOX_API_KEY or ''}", "method": "GET"},
            "OpenAI": {"url": "https://api.openai.com/v1/models", "method": "GET", "headers": {"Authorization": f"Bearer {settings.OPENAI_API_KEY or ''}"}}
        }

        timeout = 10.0
        current_time = datetime.now(timezone.utc)

        try:
            async with httpx.AsyncClient(timeout=timeout) as client:
                tasks = {}
                targets = {target_api: api_definitions[target_api]} if target_api and target_api in api_definitions else api_definitions

                for key, config in targets.items():
                    if config["method"] == "GET":
                        tasks[key] = client.get(config["url"], headers=config.get("headers", {}))
                    elif config["method"] == "POST":
                        tasks[key] = client.post(config["url"], data=config.get("data", {}), headers=config.get("headers", {}))
                    elif config["method"] == "INTERNAL":
                        async def mock_internal():
                            class MockResponse:
                                status_code = 200
                            return MockResponse()
                        tasks[key] = mock_internal()

                keys = list(tasks.keys())
                responses = await asyncio.gather(*tasks.values(), return_exceptions=True)

                for key, response in zip(keys, responses):
                    endpoint_clean_url = api_definitions[key]["url"].split("?")[0]
                    
                    record = db.query(SystemHealthStatus).filter(SystemHealthStatus.api_name == key).first()
                    if not record:
                        record = SystemHealthStatus(api_name=key)
                        db.add(record)

                    record.endpoint = endpoint_clean_url
                    record.last_checked = current_time

                    if isinstance(response, Exception):
                        record.status = "DOWN"
                        record.status_code = None
                        record.status_description = f"Connection Failed: {str(response)}"
                    else:
                        is_up = response.status_code < 500
                        record.status = "UP" if is_up else "DOWN"
                        record.status_code = response.status_code
                        record.status_description = HTTP_STATUS_DESCRIPTIONS.get(
                            response.status_code, 
                            f"Unknown HTTP Status Received ({response.status_code})"
                        )

            db.commit()
            print(f"✅ [HEALTH] {'API ' + target_api if target_api else 'All endpoints'} check complete.")
            
        except Exception as e:
            print(f"❌ [HEALTH] Critical error during ping loop: {str(e)}")

    async def _background_ping(self):
        db = SessionLocal()
        try:
            await self.ping_endpoints(db)
        finally:
            db.close()

    async def get_full_health_report(self, db: Session, background_tasks, force_refresh: bool = False, target_api: str = None):
        if target_api:
            await self.ping_endpoints(db, target_api)
        elif force_refresh:
            await self.ping_endpoints(db)

        db_records = db.query(SystemHealthStatus).all()
        
        internal_system = {
            "backend_api": {"status": "UNKNOWN", "endpoint": "Internal Database", "status_code": None, "status_description": "Pending...", "timestamp": None},
            "frontend_app": {"status": "UNKNOWN", "endpoint": "Frontend Service", "status_code": None, "status_description": "Pending...", "timestamp": None}
        }
        external_apis_list = []
        oldest_check = None
        
        for r in db_records:
            safe_dt = r.last_checked
            if safe_dt and safe_dt.tzinfo is None:
                safe_dt = safe_dt.replace(tzinfo=timezone.utc)

            data_dict = {
                "api_name": r.api_name,
                "endpoint": r.endpoint,
                "status_code": r.status_code,
                "status": r.status,
                "status_description": r.status_description,
                "last_checked": safe_dt.isoformat() if safe_dt else None
            }
            
            if r.api_name in ["backend_api", "frontend_app"]:
                data_dict["timestamp"] = data_dict["last_checked"] 
                internal_system[r.api_name] = data_dict
            else:
                external_apis_list.append(data_dict)
                if safe_dt:
                    if not oldest_check or safe_dt < oldest_check:
                        oldest_check = safe_dt

        now = datetime.now(timezone.utc)
        if oldest_check and oldest_check.tzinfo is None:
             oldest_check = oldest_check.replace(tzinfo=timezone.utc)

        if not target_api and not force_refresh:
            is_expired = not oldest_check or (now - oldest_check) > self.cache_ttl
            if is_expired:
                background_tasks.add_task(self._background_ping)

        return {
            "internal_system": internal_system,
            "external_apis": external_apis_list,
            "external_apis_last_checked": oldest_check.isoformat() if oldest_check else None,
            "next_external_check_due": (oldest_check + self.cache_ttl).isoformat() if oldest_check else "Now"
        }

health_service = HealthService()