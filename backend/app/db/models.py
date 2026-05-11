import uuid
import enum
import random
import string
from datetime import datetime, timezone
from sqlalchemy import Column, Boolean, Integer, String, Float, ForeignKey, DateTime, Text, Enum as SQLEnum, JSON
from sqlalchemy.orm import relationship
from app.core.enums import PlaceType, EventCategory, GenderEnum, UserRole, DevicePlatform, VisibilityEnum, BookingType, BookingStatus
from app.db.database import Base

def generate_travel_id():
    """Generates an 8-character string: '#' followed by 7 alphanumeric chars."""
    chars = string.ascii_uppercase + string.digits
    return "#" + ''.join(random.choices(chars, k=7))

# --- DATABASE MODELS ---
#Destination Model
class Destination(Base):
    __tablename__ = "destinations"

    id = Column(Integer, primary_key=True, index=True)
    osm_id = Column(String, index=True, nullable=True) 
    name = Column(String, index=True, nullable=False) # title
    
    # Geographic Data
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    place_name = Column(String, nullable=True) # Full descriptive name
    state_code = Column(String(2), index=True, nullable=True)
    country_code = Column(String(2), default="US")
    
    # Categorization & Description
    category = Column(String, index=True, nullable=True) # Coastal Escapes, etc.
    description = Column(Text, nullable=True)
    image_url = Column(String, nullable=True)
    
    # Pricing & Popularity
    avg_flight_price = Column(Float, nullable=True)
    avg_hotel_price = Column(Float, nullable=True)
    popularity_score = Column(Integer, default=0)

    # Relationships
    events = relationship("Event", back_populates="destination", cascade="all, delete-orphan")    

#Event Model
class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, index=True, nullable=False)
    description = Column(Text, nullable=True)
    
    # Categorization
    category = Column(SQLEnum(EventCategory), index=True, nullable=False)
    
    # Timing
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=True)
    
    # Location
    destination_id = Column(Integer, ForeignKey("destinations.id"), nullable=False)
    address = Column(String, nullable=True)
    venue_name = Column(String, nullable=True)
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    
    # Ticketing & Media
    price_min = Column(Float, nullable=True)
    price_max = Column(Float, nullable=True)
    ticket_url = Column(String, nullable=True)
    image_url = Column(String, nullable=True)

    # Relationships
    destination = relationship("Destination", back_populates="events")
    bookings = relationship("Booking", back_populates="event", cascade="all, delete-orphan")

#User Model
class User(Base):
    __tablename__ = "users"

    # --- PRIMARY IDENTIFIER ---
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    # --- BUSINESS / TRAVEL IDENTITY ---
    business_id = Column(String(36), nullable=True, index=True) 
    unique_travel_id = Column(String(8), unique=True, index=True, default=generate_travel_id, nullable=False)

    # --- PERSONAL IDENTITY ---
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=False)
    suffix = Column(String(20), nullable=True)
    profile_picture_url = Column(String, nullable=True)
    gender = Column(SQLEnum(GenderEnum), default=GenderEnum.PREFER_NOT_TO_SAY, nullable=True)

    # --- CONTACT INFORMATION ---
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone_country_code = Column(String(5), nullable=True, default="+1") 
    phone_number = Column(String(20), unique=True, index=True, nullable=True) 

    # --- PREFERENCES ---
    locale = Column(String(10), default="en-US")
    timezone = Column(String(50), default="UTC")

    # --- SECURITY & AUTHENTICATION ---
    hashed_password = Column(String(255), nullable=False)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
    is_active = Column(Boolean, default=True)
    is_locked = Column(Boolean, default=False)
    failed_login_attempts = Column(Integer, default=0)
    
    # --- OTP & VERIFICATION ---
    is_email_verified = Column(Boolean, default=False)
    email_verification_code = Column(String(6), nullable=True)
    email_verification_code_expires = Column(DateTime(timezone=True), nullable=True)
    
    is_phone_verified = Column(Boolean, default=False)
    phone_verification_code = Column(String(6), nullable=True)
    phone_verification_code_expires = Column(DateTime(timezone=True), nullable=True)
    
    # --- MFA & PASSWORD RESET ---
    mfa_enabled = Column(Boolean, default=False)
    mfa_secret = Column(String(255), nullable=True)
    reset_code = Column(String(6), nullable=True)
    reset_code_expires = Column(DateTime(timezone=True), nullable=True)

    # --- AUDIT & COMPLIANCE ---
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_login_at = Column(DateTime(timezone=True), nullable=True)
    deleted_at = Column(DateTime(timezone=True), nullable=True)

    # --- RELATIONS ---
    itineraries = relationship("SavedItinerary", back_populates="owner", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")
    bookings = relationship("Booking", back_populates="user", cascade="all, delete-orphan")

#Saved Itinerary Model
class SavedItinerary(Base):
    __tablename__ = "saved_itineraries"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    destination = Column(String(255), index=True)
    data = Column(JSON, nullable=False, default=dict) 
    visibility = Column(SQLEnum(VisibilityEnum), default=VisibilityEnum.PRIVATE, nullable=False)
    share_token = Column(String(64), unique=True, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    
    owner = relationship("User", back_populates="itineraries")
    # Add/Update the reverse relationship to point to "itinerary"
    bookings = relationship("Booking", back_populates="itinerary", cascade="all, delete-orphan")

#Booking Model
class Booking(Base):
    __tablename__ = "bookings"

    # Primary Keys & Foreign Keys
    id = Column(Integer, index=True, primary_key=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=True)
    user_id = Column(String(36), ForeignKey("users.id"), nullable=False) # Changed to String(36) to match User.id
    
    # RENAMED and FIXED TYPE (SavedItinerary uses String(36) UUIDs, not Integers)
    itinerary_id = Column(String(36), ForeignKey("saved_itineraries.id"), nullable=True) 

    # Core Details
    booking_type = Column(SQLEnum(BookingType), index=True, nullable=False)
    confirmation_code = Column(String, nullable=True)
    end_date = Column(DateTime, nullable=True)
    notes = Column(Text, nullable=True)
    provider_name = Column(String, nullable=False)
    start_date = Column(DateTime, nullable=False)
    status = Column(SQLEnum(BookingStatus), default=BookingStatus.PENDING, index=True)
    total_price = Column(Float, nullable=False)

    # Relationships
    event = relationship("Event", back_populates="bookings")
    user = relationship("User", back_populates="bookings")
    
    # RENAMED from `trip` to `itinerary`
    itinerary = relationship("SavedItinerary", back_populates="bookings")

#System Health Status Model
class SystemHealthStatus(Base):
    __tablename__ = "system_health_status"
    id = Column(Integer, primary_key=True, index=True)
    api_name = Column(String, unique=True, index=True, nullable=False)
    endpoint = Column(String, nullable=True)
    status_code = Column(Integer, nullable=True)
    status = Column(String, nullable=False) 
    status_description = Column(String, nullable=True)
    last_checked = Column(DateTime(timezone=True), nullable=True)

#User Session
class UserSession(Base):
    __tablename__ = "user_sessions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ip_address = Column(String(50), nullable=True) 
    user_agent = Column(String(255), nullable=True)
    platform = Column(SQLEnum(DevicePlatform), default=DevicePlatform.UNKNOWN)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_activity_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    user = relationship("User", back_populates="sessions")
    events = relationship("UserEvent", back_populates="session", cascade="all, delete-orphan")

#User Event Model
class UserEvent(Base):
    __tablename__ = "user_events"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String(36), ForeignKey("user_sessions.id", ondelete="SET NULL"), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    event_category = Column(String(50), index=True, nullable=False)
    event_action = Column(String(100), nullable=False)
    event_metadata = Column(JSON, nullable=False, default=dict) 
    page_url = Column(String(255), nullable=True) 
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)
    session = relationship("UserSession", back_populates="events")

