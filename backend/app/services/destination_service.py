from sqlalchemy.orm import Session
from app.db.models import Destination
from app.schemas.destination import DestinationCreate
from app.core.enums import PlaceType

class DestinationService:
    def create_destination(self, db: Session, dest_in: DestinationCreate) -> Destination:
        db_dest = Destination(**dest_in.model_dump())
        db.add(db_dest)
        db.commit()
        db.refresh(db_dest)
        return db_dest

    def get_destination(self, db: Session, dest_id: int) -> Destination:
        return db.query(Destination).filter(Destination.id == dest_id).first()

    def search_destinations(
        self, db: Session, skip: int = 0, limit: int = 50, 
        state_code: str = None, place_type: PlaceType = None
    ):
        query = db.query(Destination)
        if state_code:
            query = query.filter(Destination.state_code == state_code)
        if place_type:
            query = query.filter(Destination.place_type == place_type)
            
        # Order by population descending to show major cities first by default
        return query.order_by(Destination.population.desc().nullslast()).offset(skip).limit(limit).all()

destination_service = DestinationService()