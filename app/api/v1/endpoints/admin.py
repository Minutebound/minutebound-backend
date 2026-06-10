from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.db.database import get_db
from app.db.models import User, UserRole, UserSession
from app.api.v1.deps import get_current_admin

router = APIRouter()

class RoleUpdateRequest(BaseModel):
    new_role: UserRole

@router.put("/users/{target_user_id}/role")
async def update_user_role(
    target_user_id: str,
    req: RoleUpdateRequest,
    db: Session = Depends(get_db),
    current_admin: User = Depends(get_current_admin) 
):
    target_user = db.query(User).filter(User.id == target_user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    if target_user.role == UserRole.SUPER_ADMIN and current_admin.role != UserRole.SUPER_ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Only a Super Admin can modify another Super Admin."
        )

    target_user.role = req.new_role
    db.commit()
    
    return {
        "message": f"Successfully updated user to {req.new_role}",
        "user_email": target_user.email,
        "new_role": target_user.role
    }

@router.get("/users/all")
def get_all_users(db: Session = Depends(get_db), current_admin: User = Depends(get_current_admin)):
    users = db.query(User).all()
    return [{"email": u.email, "role": u.role, "id": str(u.id)} for u in users]

@router.get("/sessions")
def get_all_sessions(
    limit: int = 50, 
    db: Session = Depends(get_db), 
    current_admin: User = Depends(get_current_admin)
):
    """
    Enterprise Standard: Admins can view the most recent user sessions.
    """
    sessions = (
        db.query(UserSession)
        .order_by(UserSession.started_at.desc()) # Newest first
        .limit(limit)
        .all()
    )
    
    # We map it to a dictionary to safely handle the UUIDs and Dates for JSON
    return [
        {
            "session_id": str(s.id),
            "user_id": str(s.user_id),
            "platform": s.platform,
            "ip_address": s.ip_address,
            "started_at": s.started_at,
            "last_activity_at": s.last_activity_at,
            "is_active": s.is_active
        }
        for s in sessions
    ]