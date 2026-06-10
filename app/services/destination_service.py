import httpx
from sqlalchemy.orm import Session
from sqlalchemy import or_
from app.db.models import Destination
from app.schemas.destination import DestinationCreate
from app.providers.destinations.serp_provider import SerpDestinationProvider

class DestinationService:
    def __init__(self):
        self.serp = SerpDestinationProvider()

    async def get_top_destinations(self, db: Session):
        """Combines top manual entries with live SerpApi trends."""
        db_top = db.query(Destination).order_by(Destination.popularity_score.desc()).limit(10).all()
        serp_trends = await self.serp.get_popular_destinations()
        return {
            "featured": db_top,
            "trending": serp_trends
        }

    async def get_or_fetch_destination_meta(self, db: Session, name: str, place_name: str = None, lat: float = 0.0, lon: float = 0.0):
        """Fetches from DB first. If not found, calls Wikipedia, saves to DB, and returns."""
        clean_city = name.split(',')[0].strip()
        
        # 1. Search in DB by name
        db_dest = db.query(Destination).filter(Destination.name.ilike(f"%{clean_city}%")).first()
        
        # If it exists AND has a description/fun fact already, just return it
        if db_dest and db_dest.description and db_dest.fun_fact:
            db_dest.popularity_score = (db_dest.popularity_score or 0) + 1
            db.commit()
            return db_dest

        # 2. Not fully populated in DB? Fetch from Wikipedia
        try:
            headers = {
                        "User-Agent": "MinuteBoundTravelApp/1.0 (contact@minutebound.com)"
                        }
            async with httpx.AsyncClient() as client:
                wiki_res = await client.get(f"https://en.wikipedia.org/api/rest_v1/page/summary/{clean_city}",headers=headers)
                wiki_res.raise_for_status()
                wiki_data = wiki_res.json()
            
            # Extract description
            description = wiki_data.get("extract", "A beautiful destination waiting to be explored.")
            
            # Extract sentences to formulate a "Fun Fact"
            sentences = description.split('. ')
            fun_fact = f"{sentences[1]}." if len(sentences) > 1 else "Local culture and history run deep here."
            
            # Extract best quality image
            image_url = None
            if "originalimage" in wiki_data:
                image_url = wiki_data["originalimage"].get("source")
            elif "thumbnail" in wiki_data:
                image_url = wiki_data["thumbnail"].get("source")
            
            if not image_url:
                image_url = "https://images.unsplash.com/photo-1436491865332-7a61a109cc05?q=80&w=2000&auto=format&fit=crop"

            # 3. Save or Update in DB
            if not db_dest:
                db_dest = Destination(
                    name=clean_city,
                    place_name=place_name or name,
                    latitude=lat,
                    longitude=lon,
                    description=description,
                    fun_fact=fun_fact,
                    image_url=image_url,
                    popularity_score=1
                )
                db.add(db_dest)
            else:
                db_dest.description = description
                db_dest.fun_fact = fun_fact
                if image_url:
                    db_dest.image_url = image_url
                db_dest.popularity_score = (db_dest.popularity_score or 0) + 1
            
            db.commit()
            db.refresh(db_dest)
            return db_dest

        except Exception as e:
            print(f"Failed to fetch Wiki data for {clean_city}: {e}")
            
            # Fallback gracefully so the frontend never crashes
            if not db_dest:
                db_dest = Destination(
                    name=clean_city, 
                    place_name=place_name or name, 
                    latitude=lat, 
                    longitude=lon, 
                    description="Get ready for an unforgettable journey. Experience the local sights, sounds, and culture.", 
                    fun_fact="Adventure awaits around every corner.", 
                    image_url="https://images.unsplash.com/photo-1436491865332-7a61a109cc05?q=80&w=2000&auto=format&fit=crop",
                    popularity_score=1
                )
                db.add(db_dest)
                db.commit()
                db.refresh(db_dest)
            return db_dest

    def create_destination(self, db: Session, dest_in: DestinationCreate) -> Destination:
        db_dest = Destination(**dest_in.model_dump())
        db.add(db_dest)
        db.commit()
        db.refresh(db_dest)
        return db_dest

    def search_destinations(self, db: Session, skip: int = 0, limit: int = 50, query: str = None, state_code: str = None, category: str = None):
        db_query = db.query(Destination)
        if query:
            db_query = db_query.filter(
                or_(
                    Destination.name.ilike(f"%{query}%"),
                    Destination.place_name.ilike(f"%{query}%")
                )
            )
        if state_code:
            db_query = db_query.filter(Destination.state_code == state_code)
        if category:
            db_query = db_query.filter(Destination.category == category)
            
        return db_query.order_by(Destination.popularity_score.desc()).offset(skip).limit(limit).all()

    def get_destination(self, db: Session, dest_id: int) -> Destination:
        return db.query(Destination).filter(Destination.id == dest_id).first()

destination_service = DestinationService()