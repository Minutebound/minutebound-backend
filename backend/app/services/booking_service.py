from sqlalchemy.orm import Session
from app.db.models import Booking
from app.schemas.booking import BookingCreate

class BookingService:
    def create_booking(self, booking_in: BookingCreate, db: Session, user_id: str):
        """Creates a new booking record attached to a user ID."""
        db_booking = Booking(
            **booking_in.dict(), 
            user_id=user_id
        )
        db.add(db_booking)
        db.commit()
        db.refresh(db_booking)
        return db_booking

    def get_all_bookings(self, db: Session, limit: int = 100, skip: int = 0):
        """Fetches all bookings (Used for Admin Dashboard)."""
        return db.query(Booking).order_by(Booking.start_date.desc()).offset(skip).limit(limit).all()

    def get_booking_by_id(self, booking_id: int, db: Session):
        """Fetches a single booking by its primary ID."""
        return db.query(Booking).filter(Booking.id == booking_id).first()

    def get_user_bookings(self, db: Session, user_id: str, limit: int = 100, skip: int = 0):
        """Fetches all bookings belonging to a specific user (Used for My Bookings page)."""
        return db.query(Booking).filter(Booking.user_id == user_id).order_by(Booking.start_date.desc()).offset(skip).limit(limit).all()

booking_service = BookingService()