from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import datetime, timedelta, timezone
import random
import string
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

from app.core.security import verify_password, get_password_hash, create_access_token, ACCESS_TOKEN_EXPIRE_MINUTES
from app.schemas.auth import (
    Token, UserCreate, UserLogin, ForgotPassword, ResetPassword, 
    VerifyEmailOTP, ResendEmailOTP, VerifyPhoneOTP, ResendPhoneOTP
)
from app.db.database import get_db
from app.db.models import User

router = APIRouter()

def generate_otp() -> str:
    return ''.join(random.choices(string.digits, k=6))

def send_otp_email(to_email: str, code: str, purpose: str = "verification"):
    sender_email = settings.SMTP_USERNAME
    sender_password = settings.SMTP_PASSWORD
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = to_email
        
        if purpose == "verification":
            msg['Subject'] = "WanderPlan US - Verify Your Email"
            body = f"Welcome to WanderPlan!\n\nYour email verification code is: {code}\n\nThis code will expire in 15 minutes."
        else:
            msg['Subject'] = "WanderPlan US - Password Reset Code"
            body = f"Your password reset code is: {code}\n\nThis code will expire in 15 minutes."
            
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
        print(f"Sent {purpose} OTP email to {to_email}")
    except Exception as e:
        print(f"Failed to send email to {to_email}: {e}")
        print(f"--- LOCAL DEV FALLBACK: {purpose.upper()} EMAIL CODE FOR {to_email} IS [{code}] ---")

def send_otp_sms(phone_country_code: str, phone_number: str, code: str):
    """
    Mock function for sending SMS. In production, integrate Twilio, AWS SNS, or MessageBird here.
    """
    full_number = f"{phone_country_code}{phone_number}"
    print(f"--- LOCAL DEV FALLBACK: SMS OTP FOR {full_number} IS [{code}] ---")
    # TODO: Add Twilio logic here

@router.post("/signup", response_model=Token)
async def sign_up(user_in: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_in.email).first()
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    hashed_password = get_password_hash(user_in.password)
    
    email_code = generate_otp()
    
    new_user = User(
        email=user_in.email, 
        hashed_password=hashed_password,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        middle_name=user_in.middle_name,
        suffix=user_in.suffix,
        phone_country_code=user_in.phone_country_code,
        phone_number=user_in.phone_number,
        
        # Explicitly Unverified
        is_email_verified=False, 
        is_phone_verified=False,
        
        email_verification_code=email_code,
        email_verification_code_expires=datetime.now(timezone.utc) + timedelta(minutes=15)
    )
    
    # If they provided a phone number at signup, generate a code for that too
    if user_in.phone_number:
        phone_code = generate_otp()
        new_user.phone_verification_code = phone_code
        new_user.phone_verification_code_expires = datetime.now(timezone.utc) + timedelta(minutes=15)
        send_otp_sms(user_in.phone_country_code, user_in.phone_number, phone_code)
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    # Send Email
    send_otp_email(new_user.email, email_code, purpose="verification")
    
    access_token = create_access_token(
        data={"sub": new_user.email}, 
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer", "email": new_user.email, "status_code": 200}

@router.post("/verify-email")
async def verify_email(req: VerifyEmailOTP, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user: raise HTTPException(status_code=404, detail="User not found.")
    if user.is_email_verified: return {"message": "Email is already verified.", "status_code": 200}

    now = datetime.now(timezone.utc)
    if not user.email_verification_code or user.email_verification_code != req.code:
        raise HTTPException(status_code=400, detail="Invalid verification code.")
    if not user.email_verification_code_expires or user.email_verification_code_expires < now:
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new one.")
        
    user.is_email_verified = True
    user.email_verification_code = None
    user.email_verification_code_expires = None
    db.commit()
    return {"message": "Email verified successfully.", "status_code": 200}

@router.post("/verify-phone")
async def verify_phone(req: VerifyPhoneOTP, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user: raise HTTPException(status_code=404, detail="User not found.")
    if user.is_phone_verified: return {"message": "Phone is already verified.", "status_code": 200}

    now = datetime.now(timezone.utc)
    if not user.phone_verification_code or user.phone_verification_code != req.phone_code:
        raise HTTPException(status_code=400, detail="Invalid phone verification code.")
    if not user.phone_verification_code_expires or user.phone_verification_code_expires < now:
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new one.")
        
    user.is_phone_verified = True
    user.phone_verification_code = None
    user.phone_verification_code_expires = None
    db.commit()
    return {"message": "Phone number verified successfully.", "status_code": 200}

@router.post("/resend-email-verification")
async def resend_email_verification(req: ResendEmailOTP, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or user.is_email_verified: 
        return {"message": "If that email is registered and unverified, a new code has been sent.", "status_code": 200}
        
    new_code = generate_otp()
    user.email_verification_code = new_code
    user.email_verification_code_expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    db.commit()
    
    send_otp_email(user.email, new_code, purpose="verification")
    return {"message": "If that email is registered and unverified, a new code has been sent.", "status_code": 200}

@router.post("/resend-phone-verification")
async def resend_phone_verification(req: ResendPhoneOTP, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.phone_number or user.is_phone_verified:
        return {"message": "If that phone is registered and unverified, a new code has been sent.", "status_code": 200}
        
    new_code = generate_otp()
    user.phone_verification_code = new_code
    user.phone_verification_code_expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    db.commit()
    
    send_otp_sms(user.phone_country_code, user.phone_number, new_code)
    return {"message": "If that phone is registered and unverified, a new code has been sent.", "status_code": 200}

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_credentials.email).first()
    if not db_user or not verify_password(user_credentials.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
        
    access_token = create_access_token(
        data={"sub": db_user.email}, 
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer", "email": db_user.email, "status_code": 200}

@router.post("/swagger-login", response_model=Token, include_in_schema=False)
async def swagger_login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == form_data.username).first()
    if not db_user or not verify_password(form_data.password, db_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect email or password")
    access_token = create_access_token(
        data={"sub": db_user.email}, 
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer", "email": db_user.email, "status_code": 200}

@router.post("/forgot-password")
async def forgot_password(req: ForgotPassword, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user: return {"message": "If that email is registered, a reset code has been sent.", "status_code": 200}
        
    code = generate_otp()
    user.reset_code = code
    user.reset_code_expires = datetime.now(timezone.utc) + timedelta(minutes=15)
    db.commit()
    
    send_otp_email(user.email, code, purpose="password reset")
    return {"message": "If that email is registered, a reset code has been sent.", "status_code": 200}

@router.post("/reset-password")
async def reset_password(req: ResetPassword, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or user.reset_code != req.code:
        raise HTTPException(status_code=400, detail="Invalid email or verification code.")
        
    now = datetime.now(timezone.utc)
    if not user.reset_code_expires or user.reset_code_expires < now:
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new one.")
        
    user.hashed_password = get_password_hash(req.new_password)
    user.reset_code = None
    user.reset_code_expires = None
    db.commit()
    return {"message": "Password reset successfully. You can now log in.", "status_code": 200}