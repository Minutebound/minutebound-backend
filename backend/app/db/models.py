import uuid
import enum
import random
import string
from datetime import datetime, timezone
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Integer, Enum, JSON
from sqlalchemy.orm import relationship
from app.db.database import Base

def generate_travel_id():
    """Generates an 8-character string: '#' followed by 7 alphanumeric chars."""
    chars = string.ascii_uppercase + string.digits
    return "#" + ''.join(random.choices(chars, k=7))

class VisibilityEnum(str, enum.Enum):
    PRIVATE = "PRIVATE"
    SHARED = "SHARED"
    PUBLIC = "PUBLIC"

class UserRole(str, enum.Enum):
    USER = "USER"
    SUPPORT = "SUPPORT"
    ADMIN = "ADMIN"
    SUPER_ADMIN = "SUPER_ADMIN"

class DevicePlatform(str, enum.Enum):
    WEB = "WEB"
    IOS = "IOS"
    ANDROID = "ANDROID"
    UNKNOWN = "UNKNOWN"

class User(Base):
    __tablename__ = "users"

    # --- PRIMARY IDENTIFIER ---
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)

    # --- BUSINESS / TRAVEL IDENTITY ---
    business_id = Column(String(36), nullable=True, index=True) # Future-proofing for business travel
    unique_travel_id = Column(String(8), unique=True, index=True, default=generate_travel_id, nullable=False)

    # --- PERSONAL IDENTITY ---
    first_name = Column(String(100), nullable=False)
    middle_name = Column(String(100), nullable=True)
    last_name = Column(String(100), nullable=False)
    suffix = Column(String(20), nullable=True)
    profile_picture_url = Column(String, nullable=True)

    # --- CONTACT INFORMATION ---
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone_country_code = Column(String(5), nullable=True, default="+1") 
    phone_number = Column(String(20), unique=True, index=True, nullable=True) 

    # --- PREFERENCES ---
    locale = Column(String(10), default="en-US")
    timezone = Column(String(50), default="UTC")

    # --- SECURITY & AUTHENTICATION ---
    hashed_password = Column(String(255), nullable=False)
    role = Column(Enum(UserRole), default=UserRole.USER, nullable=False)
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
    trips = relationship("SavedTrip", back_populates="owner", cascade="all, delete-orphan")
    sessions = relationship("UserSession", back_populates="user", cascade="all, delete-orphan")

class SavedTrip(Base):
    __tablename__ = "saved_trips"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    destination = Column(String(255), index=True)
    data = Column(JSON, nullable=False, default=dict) 
    visibility = Column(Enum(VisibilityEnum), default=VisibilityEnum.PRIVATE, nullable=False)
    share_token = Column(String(64), unique=True, index=True, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    deleted_at = Column(DateTime(timezone=True), nullable=True)
    owner = relationship("User", back_populates="trips")

class SystemHealthStatus(Base):
    __tablename__ = "system_health_status"
    id = Column(Integer, primary_key=True, index=True)
    api_name = Column(String, unique=True, index=True, nullable=False)
    endpoint = Column(String, nullable=True)
    status_code = Column(Integer, nullable=True)
    status = Column(String, nullable=False) 
    status_description = Column(String, nullable=True)
    last_checked = Column(DateTime(timezone=True), nullable=True)

class UserSession(Base):
    __tablename__ = "user_sessions"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()), index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    ip_address = Column(String(50), nullable=True) 
    user_agent = Column(String(255), nullable=True)
    platform = Column(Enum(DevicePlatform), default=DevicePlatform.UNKNOWN)
    started_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    last_activity_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    ended_at = Column(DateTime(timezone=True), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    user = relationship("User", back_populates="sessions")
    events = relationship("UserEvent", back_populates="session", cascade="all, delete-orphan")

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