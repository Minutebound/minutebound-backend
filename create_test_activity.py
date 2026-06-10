import uuid
import json
from datetime import datetime, timezone, timedelta
from app.db.database import SessionLocal
from app.db.models import User, UserSession, UserEvent, DevicePlatform

def create_sample_activity(email: str):
    db = SessionLocal()
    
    # 1. Find the target user
    user = db.query(User).filter(User.email == email).first()
    if not user:
        print(f"❌ User with email {email} not found! Run create_admin.py first.")
        db.close()
        return

    print(f"Generating test activity for {user.first_name} ({email})...")

    # 2. Create a Mock Session
    # Generating a session that started 30 minutes ago
    session_id = str(uuid.uuid4())
    new_session = UserSession(
        id=session_id,
        user_id=user.id,
        ip_address="127.0.0.1",
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Chrome/124.0.0.0 Safari/537.36",
        platform=DevicePlatform.WEB,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=30),
        last_activity_at=datetime.now(timezone.utc),
        is_active=True
    )
    db.add(new_session)
    print(f"✅ Session created: {session_id}")

    # 3. Create Mock Events
    # Event 1: Page View (Landing)
    event1 = UserEvent(
        id=str(uuid.uuid4()),
        session_id=session_id,
        user_id=user.id,
        event_category="NAVIGATION",
        event_action="PAGE_VIEW",
        event_metadata={"path": "/", "referrer": "direct"},
        page_url="http://localhost:3000/",
        created_at=datetime.now(timezone.utc) - timedelta(minutes=28)
    )

    # Event 2: Initiated Search
    event2 = UserEvent(
        id=str(uuid.uuid4()),
        session_id=session_id,
        user_id=user.id,
        event_category="TRIP_SEARCH",
        event_action="INITIATED_SEARCH",
        event_metadata={
            "origin": "New York, NY",
            "destination": "Paris, France",
            "travel_mode": "fly",
            "budget": "Premium"
        },
        page_url="http://localhost:3000/",
        created_at=datetime.now(timezone.utc) - timedelta(minutes=25)
    )

    # Event 3: Saved Trip
    event3 = UserEvent(
        id=str(uuid.uuid4()),
        session_id=session_id,
        user_id=user.id,
        event_category="TRIP_INTERACTION",
        event_action="SAVE_TRIP",
        event_metadata={"trip_id": str(uuid.uuid4()), "destination": "Paris"},
        page_url="http://localhost:3000/results",
        created_at=datetime.now(timezone.utc) - timedelta(minutes=20)
    )

    db.add_all([event1, event2, event3])
    db.commit()
    
    print(f"✅ 3 Test Events created for session {session_id}")
    print("\n🚀 You can now check http://localhost:8000/docs under the Admin/Analytics sections to see this data!")
    db.close()

if __name__ == "__main__":
    # Replace with the user you want to add activity for
    TEST_USER_EMAIL = "admin@minutebound.com" 
    create_sample_activity(TEST_USER_EMAIL)