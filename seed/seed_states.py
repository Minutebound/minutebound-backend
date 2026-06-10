import uuid
from sqlalchemy.orm import Session
from app.db.database import SessionLocal, Base, engine
from app.db.models import Country, State

# Standard list of US States and DC
US_STATES = {
    "AL": "Alabama", "AK": "Alaska", "AZ": "Arizona", "AR": "Arkansas", "CA": "California",
    "CO": "Colorado", "CT": "Connecticut", "DE": "Delaware", "DC": "District of Columbia",
    "FL": "Florida", "GA": "Georgia", "HI": "Hawaii", "ID": "Idaho", "IL": "Illinois",
    "IN": "Indiana", "IA": "Iowa", "KS": "Kansas", "KY": "Kentucky", "LA": "Louisiana",
    "ME": "Maine", "MD": "Maryland", "MA": "Massachusetts", "MI": "Michigan", "MN": "Minnesota",
    "MS": "Mississippi", "MO": "Missouri", "MT": "Montana", "NE": "Nebraska", "NV": "Nevada",
    "NH": "New Hampshire", "NJ": "New Jersey", "NM": "New Mexico", "NY": "New York",
    "NC": "North Carolina", "ND": "North Dakota", "OH": "Ohio", "OK": "Oklahoma", "OR": "Oregon",
    "PA": "Pennsylvania", "RI": "Rhode Island", "SC": "South Carolina", "SD": "South Dakota",
    "TN": "Tennessee", "TX": "Texas", "UT": "Utah", "VT": "Vermont", "VA": "Virginia",
    "WA": "Washington", "WV": "West Virginia", "WI": "Wisconsin", "WY": "Wyoming"
}

def seed_database():
    print("🌱 Starting database seed...")
    db: Session = SessionLocal()

    try:
        # 1. Ensure the United States exists in the Country table
        us_country = db.query(Country).filter(Country.country_code == "US").first()
        
        if not us_country:
            print("🇺🇸 Creating United States country record...")
            us_country = Country(
                id=str(uuid.uuid4()),
                country_code="US",
                iso3="USA",
                name="United States" # <-- UPDATED from 'name'
            )
            db.add(us_country)
            db.commit()
            db.refresh(us_country)
        else:
            print("🇺🇸 United States already exists in DB.")

        # 2. Iterate through states and insert if they don't exist
        states_added = 0
        for state_code, state_name_value in US_STATES.items():
            existing_state = db.query(State).filter(
                State.country_id == us_country.id,
                State.state_code == state_code
            ).first()

            if not existing_state:
                new_state = State(
                    id=str(uuid.uuid4()),
                    country_id=us_country.id,
                    state_code=state_code,
                    name=state_name_value, # <-- UPDATED from 'name'
                    is_sot_restricted=False 
                )
                db.add(new_state)
                states_added += 1

        if states_added > 0:
            db.commit()
            print(f"✅ Successfully added {states_added} new states!")
        else:
            print("✅ All states are already present in the database.")

    except Exception as e:
        print(f"❌ Error during seeding: {e}")
        db.rollback()
    finally:
        db.close()
        print("🏁 Seeding complete.")

if __name__ == "__main__":
    # Ensure tables are created before seeding
    Base.metadata.create_all(bind=engine)
    seed_database()