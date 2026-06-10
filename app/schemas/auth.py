from pydantic import BaseModel, EmailStr, Field
from typing import List, Optional
from enum import Enum as PyEnum

# Replicate the Enum in schemas for validation
class GenderEnum(str, PyEnum):
    MALE = "MALE"
    FEMALE = "FEMALE"
    PREFER_NOT_TO_SAY = "PREFER_NOT_TO_SAY"
    OTHER = "OTHER"

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    middle_name: str | None = Field(None, max_length=100)
    suffix: str | None = Field(None, max_length=20)
    business_id: str | None = Field(None, max_length=36)

    # --- ADDED GENDER FIELD ---
    gender: GenderEnum | None = Field(default=GenderEnum.PREFER_NOT_TO_SAY)

    # --- ADDED RESIDENCE ---
    residence_place: str | None = Field(None, max_length=255)

    # Optional phone at signup
    phone_country_code: str | None = Field(None, pattern=r"^\+\d{1,4}$")
    phone_number: str | None = Field(None, min_length=7, max_length=20)

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class Token(BaseModel):
    access_token: str
    token_type: str
    email: str
    status_code: int = 200

class ForgotPassword(BaseModel):
    email: EmailStr

class ResetPassword(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)
    new_password: str

# --- EMAIL OTP SCHEMAS ---
class VerifyEmailOTP(BaseModel):
    email: EmailStr
    code: str = Field(..., min_length=6, max_length=6)

class ResendEmailOTP(BaseModel):
    email: EmailStr

# --- PHONE OTP SCHEMAS ---
class VerifyPhoneOTP(BaseModel):
    email: EmailStr
    phone_code: str = Field(..., min_length=6, max_length=6)

class ResendPhoneOTP(BaseModel):
    email: EmailStr

# --- PROFILE RESPONSE (used by /users/me) ---
class UserProfileResponse(BaseModel):
    username: str
    first_name: str
    middle_name: Optional[str] = None
    last_name: str
    suffix: Optional[str] = None
    full_name: str
    email: EmailStr
    is_email_verified: bool
    phone_country_code: Optional[str] = None
    phone_number: Optional[str] = None
    mobile_number: Optional[str] = None
    residence_place: Optional[str] = None
    # Primary single picture kept for backward compatibility
    profile_picture_url: Optional[str] = None
    # New: list of picture URLs
    profile_picture_urls: List[str] = Field(default_factory=list)
    role: str
    unique_travel_id: str