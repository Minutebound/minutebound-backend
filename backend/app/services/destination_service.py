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
        # 1. Get manually curated destinations from DB
        db_top = db.query(Destination).order_by(Destination.popularity_score.desc()).limit(10).all()
        
        # 2. Fetch live trends from SerpApi
        serp_trends = await self.serp.get_popular_destinations()
        
        # Map Serp results to a compatible format for the frontend
        return {
            "featured": db_top,
            "trending": serp_trends
        }

    def create_destination(self, db: Session, dest_in: DestinationCreate) -> Destination:
        db_dest = Destination(**dest_in.model_dump())
        db.add(db_dest)
        db.commit()
        db.refresh(db_dest)
        return db_dest

    def search_destinations(
        self, db: Session, skip: int = 0, limit: int = 50, 
        query: str = None, state_code: str = None, category: str = None
    ):
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