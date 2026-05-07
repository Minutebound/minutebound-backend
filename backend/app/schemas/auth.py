from pydantic import BaseModel, EmailStr, Field

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    first_name: str = Field(..., max_length=100)
    last_name: str = Field(..., max_length=100)
    middle_name: str | None = Field(None, max_length=100)
    suffix: str | None = Field(None, max_length=20)
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
    email: EmailStr # Usually use email to look up the user session
    phone_code: str = Field(..., min_length=6, max_length=6)

class ResendPhoneOTP(BaseModel):
    email: EmailStr