import uuid
import os
from fastapi import APIRouter, Depends, UploadFile, File, Form, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.db.models import User
from app.api.v1.deps import get_current_user
from app.core.config import settings

router = APIRouter()

@router.get("/me")
def get_profile(current_user: User = Depends(get_current_user)):
    full_name = f"{current_user.first_name} {current_user.last_name}".strip()
    return {
        "username": current_user.email, 
        "first_name": current_user.first_name,
        "middle_name": current_user.middle_name,
        "last_name": current_user.last_name,
        "suffix": current_user.suffix,
        "full_name": full_name,
        "email": current_user.email,
        "phone_country_code": current_user.phone_country_code,
        "phone_number": current_user.phone_number,
        "mobile_number": f"{current_user.phone_country_code or ''} {current_user.phone_number or ''}".strip(), 
        "profile_picture_url": current_user.profile_picture_url,
        "role": current_user.role
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
            # Save the file locally
            with open(file_path, "wb") as buffer:
                buffer.write(await profile_picture.read())
            
            # Since main.py mounts /static, we can access it via this route
            current_user.profile_picture_url = f"/static/{filename}"
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Failed to save profile picture locally: {str(e)}")

    db.commit()
    db.refresh(current_user)
    
    return {
        "message": "Profile updated successfully", 
        "profile_picture_url": current_user.profile_picture_url
    }