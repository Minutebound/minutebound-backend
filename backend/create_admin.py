# backend/create_admin.py
from app.db.database import SessionLocal
from app.db.models import User, UserRole
from app.core.security import get_password_hash

def create_super_admin(email: str, password: str):
    db = SessionLocal()
    
    # 1. Check if the user already exists
    existing_user = db.query(User).filter(User.email == email).first()
    
    if existing_user:
        print(f"⚠️ User {email} already exists!")
        print("Upgrading them to SUPER_ADMIN and updating their password...")
        existing_user.role = UserRole.SUPER_ADMIN
        existing_user.hashed_password = get_password_hash(password)
        db.commit()
        print("✅ Done!")
        db.close()
        return

    # 2. Create a brand new user
    print(f"Creating new SUPER_ADMIN account for {email}...")
    new_admin = User(
        email=email,
        hashed_password=get_password_hash(password),
        first_name="Super",
        last_name="Admin",
        role=UserRole.SUPER_ADMIN,
        is_email_verified=True,  # Automatically verify them so they don't need an OTP
        is_phone_verified=True
    )
    
    db.add(new_admin)
    db.commit()
    print(f"✅ Success! You can now log into Swagger UI with:")
    print(f"   Email: {email}")
    print(f"   Password: {password}")
    db.close()

if __name__ == "__main__":
    # Change these to whatever you want your admin login to be!
    ADMIN_EMAIL = "admin@minutebound.com"
    ADMIN_PASSWORD = "SuperSecretPassword123!"
    
    create_super_admin(ADMIN_EMAIL, ADMIN_PASSWORD)