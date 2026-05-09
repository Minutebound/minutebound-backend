from typing import List, Optional

from sqlalchemy.orm import Session

from app.db.models import Booking
from app.schemas.booking import BookingCreate

class BookingService:
    def create_booking(self, booking_in: BookingCreate, db: Session, user_id: int) -> Booking:
        db_booking = Booking(**booking_in.model_dump(), user_id=user_id)
        db.add(db_booking)
        db.commit()
        db.refresh(db_booking)
        return db_booking

    def delete_booking(self, booking_id: int, db: Session) -> bool:
        db_booking = self.get_booking_by_id(booking_id=booking_id, db=db)
        if db_booking:
            db.delete(db_booking)
            db.commit()
            return True
        return False

    def get_all_bookings(self, db: Session, limit: int = 100, skip: int = 0) -> List[Booking]:
        return db.query(Booking).offset(skip).limit(limit).all()

    def get_booking_by_id(self, booking_id: int, db: Session) -> Optional[Booking]:
        return db.query(Booking).filter(Booking.id == booking_id).first()

    def get_user_bookings(self, db: Session, user_id: int, limit: int = 100, skip: int = 0) -> List[Booking]:
        return db.query(Booking).filter(Booking.user_id == user_id).offset(skip).limit(limit).all()

booking_service = BookingService()