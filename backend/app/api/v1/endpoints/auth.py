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
        elif purpose == "account deletion":
            msg['Subject'] = "WanderPlan US - Account Deletion Request"
            body = f"We received a request to delete your account.\n\nYour deletion verification code is: {code}\n\nThis code will expire in 15 minutes. If you did not request this, please secure your account immediately."
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

@router.post("/signup", response_model=Token)
async def sign_up(user_in: UserCreate, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_in.email).first()
    
    hashed_password = get_password_hash(user_in.password)
    email_code = generate_otp()

    if db_user:
        if db_user.is_active:
            # Standard conflict error for active accounts
            raise HTTPException(status_code=400, detail="User already exists")
        else:
            # Reactivate soft-deleted account seamlessly
            db_user.first_name = user_in.first_name
            db_user.last_name = user_in.last_name
            db_user.middle_name = user_in.middle_name
            db_user.suffix = user_in.suffix
            db_user.business_id = user_in.business_id
            db_user.phone_country_code = user_in.phone_country_code
            db_user.phone_number = user_in.phone_number
            db_user.hashed_password = hashed_password
            
            db_user.is_active = True
            db_user.is_email_verified = False
            db_user.email_verification_code = email_code
            db_user.email_verification_code_expires = datetime.utcnow() + timedelta(minutes=15)
            db_user.deleted_at = None
            
            db.commit()
            db.refresh(db_user)
            
            send_otp_email(db_user.email, email_code, purpose="verification")
            
            access_token = create_access_token(
                data={"sub": db_user.email}, 
                expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
            )
            return {"access_token": access_token, "token_type": "bearer", "email": db_user.email, "status_code": 200}
    
    # Standard creation if totally new
    new_user = User(
        email=user_in.email, 
        hashed_password=hashed_password,
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        middle_name=user_in.middle_name,
        suffix=user_in.suffix,
        business_id=user_in.business_id,
        phone_country_code=user_in.phone_country_code,
        phone_number=user_in.phone_number,
        is_email_verified=False, 
        is_phone_verified=False,
        email_verification_code=email_code,
        email_verification_code_expires=datetime.utcnow() + timedelta(minutes=15)
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    send_otp_email(new_user.email, email_code, purpose="verification")
    
    access_token = create_access_token(
        data={"sub": new_user.email}, 
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer", "email": new_user.email, "status_code": 200}

@router.post("/login", response_model=Token)
async def login(user_credentials: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user_credentials.email).first()
    
    # Catch: Email doesn't exist OR is a soft-deleted account
    if not db_user or not db_user.is_active:
        raise HTTPException(status_code=404, detail="User not found")
        
    if not verify_password(user_credentials.password, db_user.hashed_password):
        raise HTTPException(status_code=401, detail="Incorrect password")
        
    if not db_user.is_email_verified:
        new_code = generate_otp()
        db_user.email_verification_code = new_code
        db_user.email_verification_code_expires = datetime.utcnow() + timedelta(minutes=15)
        db.commit()
        send_otp_email(db_user.email, new_code, purpose="verification")
        
        raise HTTPException(status_code=403, detail="UNVERIFIED_EMAIL")
        
    access_token = create_access_token(
        data={"sub": db_user.email}, 
        expires_delta=timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    return {"access_token": access_token, "token_type": "bearer", "email": db_user.email, "status_code": 200}

@router.post("/verify-email")
async def verify_email(req: VerifyEmailOTP, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.is_active: raise HTTPException(status_code=404, detail="User not found.")
    if user.is_email_verified: return {"message": "Email is already verified.", "status_code": 200}

    now = datetime.utcnow()
    if not user.email_verification_code or user.email_verification_code != req.code:
        raise HTTPException(status_code=400, detail="Invalid verification code.")
        
    expires = user.email_verification_code_expires
    if expires and expires.tzinfo:
        expires = expires.replace(tzinfo=None)
        
    if not expires or expires < now:
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new one.")
        
    user.is_email_verified = True
    user.email_verification_code = None
    user.email_verification_code_expires = None
    db.commit()
    return {"message": "Email verified successfully.", "status_code": 200}

@router.post("/resend-email-verification")
async def resend_email_verification(req: ResendEmailOTP, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.is_active or user.is_email_verified: 
        return {"message": "If that email is registered and unverified, a new code has been sent.", "status_code": 200}
        
    new_code = generate_otp()
    user.email_verification_code = new_code
    user.email_verification_code_expires = datetime.utcnow() + timedelta(minutes=15)
    db.commit()
    
    send_otp_email(user.email, new_code, purpose="verification")
    return {"message": "If that email is registered and unverified, a new code has been sent.", "status_code": 200}

@router.post("/forgot-password")
async def forgot_password(req: ForgotPassword, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.is_active: return {"message": "If that email is registered, a reset code has been sent.", "status_code": 200}
        
    code = generate_otp()
    user.reset_code = code
    user.reset_code_expires = datetime.utcnow() + timedelta(minutes=15)
    db.commit()
    
    send_otp_email(user.email, code, purpose="password reset")
    return {"message": "If that email is registered, a reset code has been sent.", "status_code": 200}

@router.post("/reset-password")
async def reset_password(req: ResetPassword, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == req.email).first()
    if not user or not user.is_active or user.reset_code != req.code:
        raise HTTPException(status_code=400, detail="Invalid verification code.")
        
    now = datetime.utcnow()
    expires = user.reset_code_expires
    if expires and expires.tzinfo:
        expires = expires.replace(tzinfo=None)
        
    if not expires or expires < now:
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new one.")
        
    user.hashed_password = get_password_hash(req.new_password)
    user.reset_code = None
    user.reset_code_expires = None
    db.commit()
    return {"message": "Password reset successfully. You can now log in.", "status_code": 200}