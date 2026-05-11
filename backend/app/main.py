import os
import asyncio
from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles 
from app.core.config import settings
from app.db.database import engine, Base, SessionLocal 
from app.api.v1.endpoints import admin, analytics, attractions, auth, chatbot, destinations, driving, events, flights, health, stays, itineraries, locations, tours, users, weather
from app.services.health_service import health_service
from fastapi_cache import FastAPICache
from fastapi_cache.backends.redis import RedisBackend
from redis import asyncio as aioredis
from fastapi.middleware.cors import CORSMiddleware

Base.metadata.create_all(bind=engine)

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def custom_key_builder(func, namespace: str = "", request: Request = None, response: Response = None, args: tuple = (), kwargs: dict = None):
    prefix = FastAPICache.get_prefix()
    kwargs = kwargs or {}   
    clean_params = [f"{k}={v}" for k, v in kwargs.items() if k not in ["request", "response", "db", "self"]]
    params_str = ",".join(clean_params)
    key_parts = [prefix]
    if namespace and namespace != prefix: key_parts.append(namespace)
    key_parts.append(func.__name__)
    if params_str: key_parts.append(params_str)
    final_key = ":".join(key_parts)
    final_key = final_key.replace(f"{prefix}:{prefix}", prefix)
    return final_key.replace("::", ":")

def get_application():
    _app = FastAPI(title=settings.PROJECT_NAME, version=settings.VERSION)

    _app.add_middleware(
        CORSMiddleware,
        allow_origins=[str(origin) for origin in settings.BACKEND_CORS_ORIGINS],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    os.makedirs("static/profiles", exist_ok=True)
    _app.mount("/static", StaticFiles(directory="static"), name="static")

    _app.include_router(flights.router, prefix="/api/v1/flights", tags=["flights"])
    _app.include_router(locations.router, prefix="/api/v1/locations", tags=["locations"])
    _app.include_router(destinations.router, prefix="/api/v1/destinations", tags=["destinations"])
    _app.include_router(events.router, prefix="/api/v1/events", tags=["events"])    
    _app.include_router(driving.router, prefix="/api/v1/driving", tags=["driving"])
    _app.include_router(stays.router, prefix="/api/v1/stays", tags=["stays"])    
    _app.include_router(tours.router, prefix="/api/v1/tours", tags=["tours"])
    _app.include_router(attractions.router, prefix="/api/v1/attractions", tags=["attractions"])
    _app.include_router(weather.router, prefix="/api/v1/weather", tags=["weather"])
    _app.include_router(auth.router, prefix="/api/v1/auth", tags=["auth"])
    _app.include_router(itineraries.router, prefix="/api/v1/itineraries", tags=["itineraries"])
    _app.include_router(users.router, prefix="/api/v1/users", tags=["users"]) 
    _app.include_router(chatbot.router, prefix="/api/v1/chatbot", tags=["chatbot"])
    _app.include_router(health.router, prefix="/api/v1/health", tags=["health"])
    _app.include_router(analytics.router, prefix="/api/v1/analytics", tags=["Analytics"])
    _app.include_router(admin.router, prefix="/api/v1/admin", tags=["Admin"])
    
    return _app

app = get_application()

async def automated_health_check_task():
    await asyncio.sleep(60) 
    while True:
        print("⏳ [SCHEDULER] Triggering automatic background health check...")
        db = SessionLocal()
        try:
            await health_service.ping_endpoints(db)
        except Exception as e:
            print(f"❌ [SCHEDULER] Error during automatic health check: {e}")
        finally:
            db.close()
        await asyncio.sleep(48 * 60 * 60)

@app.on_event("startup")
async def startup():
    redis_url = os.getenv("REDIS_URL", "redis://redis:6379")
    redis = aioredis.from_url(redis_url, encoding="utf8", decode_responses=False)
    FastAPICache.init(
        RedisBackend(redis), 
        prefix="minutebound-cache",
        key_builder=custom_key_builder 
    )
    app.state.redis = aioredis.from_url(redis_url, encoding="utf8", decode_responses=True)
    asyncio.create_task(automated_health_check_task())

@app.get("/")
def root():
    return {"message": "API is operational", "status": "ok"}