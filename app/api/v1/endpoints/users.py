import uuid
import os
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import User
from app.api.v1.deps import get_current_user
from app.core.config import settings

# Import OTP tools
from app.api.v1.endpoints.auth import generate_otp, send_otp_email

router = APIRouter()

class DeleteConfirm(BaseModel):
    code: str

@router.get("/me")
def get_profile(current_user: User = Depends(get_current_user)):
    full_name = " ".join(filter(None, [
        current_user.first_name, 
        current_user.middle_name, 
        current_user.last_name, 
        current_user.suffix
    ]))
    return {
        "username": current_user.email, 
        "first_name": current_user.first_name,
        "middle_name": current_user.middle_name,
        "last_name": current_user.last_name,
        "suffix": current_user.suffix,
        "full_name": full_name,
        "email": current_user.email,
        "is_email_verified": current_user.is_email_verified,
        "phone_country_code": current_user.phone_country_code,
        "phone_number": current_user.phone_number,
        "mobile_number": f"{current_user.phone_country_code or ''} {current_user.phone_number or ''}".strip(), 
        "profile_picture_url": current_user.profile_picture_url,
        "role": current_user.role,
        "unique_travel_id": current_user.unique_travel_id
    }

@router.put("/me")
async def update_profile(
    first_name: str = Form(None),
    last_name: str = Form(None),
    middle_name: str = Form(None),
    suffix: str = Form(None),
    email: str = Form(None),
    phone_country_code: str = Form(None),
    phone_number: str = Form(None),
    profile_picture: UploadFile = File(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    if not any([first_name, last_name, middle_name, suffix, email, phone_country_code, phone_number]) and (profile_picture is None or not profile_picture.filename):
        raise HTTPException(status_code=400, detail="No fields provided to update")

    if first_name is not None: current_user.first_name = first_name
    if last_name is not None: current_user.last_name = last_name
    if middle_name is not None: current_user.middle_name = middle_name
    if suffix is not None: current_user.suffix = suffix
    if email is not None: current_user.email = email
    if phone_country_code is not None: current_user.phone_country_code = phone_country_code
    if phone_number is not None: current_user.phone_number = phone_number

    if profile_picture and profile_picture.filename:
        ext = profile_picture.filename.split('.')[-1]
        filename = f"profiles/{uuid.uuid4()}.{ext}"
        file_path = os.path.join("static", filename)
        
        try:
            with open(file_path, "wb") as buffer:
                buffer.write(await profile_picture.read())
            current_user.profile_picture_url = f"/static/{filename}"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save profile picture locally: {str(e)}")

    db.commit()
    db.refresh(current_user)
    
    return {
        "message": "Profile updated successfully", 
        "profile_picture_url": current_user.profile_picture_url
    }

@router.post("/me/request-delete")
def request_account_deletion(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    code = generate_otp()
    current_user.email_verification_code = code
    current_user.email_verification_code_expires = datetime.utcnow() + timedelta(minutes=15)
    db.commit()
    
    send_otp_email(current_user.email, code, purpose="account deletion")
    return {"message": "Deletion OTP sent"}

@router.delete("/me/confirm-delete")
def confirm_account_deletion(req: DeleteConfirm, current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    now = datetime.utcnow()
    expires = current_user.email_verification_code_expires
    if expires and expires.tzinfo:
        expires = expires.replace(tzinfo=None)
    
    if not current_user.email_verification_code or current_user.email_verification_code != req.code:
        raise HTTPException(status_code=400, detail="Invalid verification code.")
        
    if not expires or expires < now:
        raise HTTPException(status_code=400, detail="Verification code has expired. Please request a new one.")
        
    db.delete(current_user)
    db.commit()
    return {"message": "Account deleted successfully."}