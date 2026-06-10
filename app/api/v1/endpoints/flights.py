import stripe
import os
import httpx
import uuid
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime
from jose import jwt

from app.api.v1.deps import get_current_user
from app.db.database import get_db
from app.db.models import User, Booking
from app.core.enums import BookingType, BookingStatus
from app.services.flight_service import flight_service
from app.schemas.flight import (
    FlightOffer, PriceConfirmRequest, FlightBookRequest, 
    PaymentIntentRequest, PriceConfirmResponse
)
from app.core.config import settings
from app.core.security import ALGORITHM

stripe.api_key = os.getenv("STRIPE_SECRET_KEY", "sk_test_mock")

router = APIRouter()

@router.get("/search", response_model=List[FlightOffer])
async def get_flights(
    origin: str, destination: str, date: str, return_date: Optional[str] = None,
    adults: int = 1, children: int = 0, travel_class: str = "ECONOMY"
):
    results = await flight_service.get_flights(
        origin=origin, destination=destination, date=date, 
        return_date=return_date, adults=adults, children=children, travel_class=travel_class
    )
    if isinstance(results, dict) and "error" in results:
        raise HTTPException(status_code=400, detail=results["error"])
    return results

@router.post("/price", response_model=PriceConfirmResponse)
async def confirm_flight_price(request: PriceConfirmRequest):
    result = await flight_service.confirm_price(request.offer_id)
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result

@router.post("/create-payment-intent")
async def create_payment_intent(request: PaymentIntentRequest):
    """
    NO AUTH REQUIRED: Guests can securely pay. 
    """
    try:
        amount_in_cents = int(request.amount * 100)
        intent = stripe.PaymentIntent.create(
            amount=amount_in_cents, currency=request.currency.lower(), capture_method="manual",
            metadata={"checkout_type": "hybrid"}
        )
        return {"client_secret": intent.client_secret, "intent_id": intent.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/book")
async def book_flight(
    request: Request,
    flight_request: FlightBookRequest, 
    db: Session = Depends(get_db)
):
    """
    Hybrid Endpoint: Identifies logged-in users via Authorization header, generates a unified
    System Booking ID, books the flight, captures Stripe, and saves to DB (if logged in).
    """
    # 1. Safely Extract User ID if Logged In
    user_id = None
    auth_header = request.headers.get("Authorization")
    if auth_header and auth_header.startswith("Bearer "):
        try:
            token = auth_header.split(" ")[1]
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
            user_email = payload.get("sub")
            if user_email:
                user = db.query(User).filter(User.email == user_email).first()
                if user:
                    user_id = user.id  
        except Exception as e:
            print(f"Auth token extraction skipped: {e}")

    # 2. Generate the Unified MinuteBound Reference ID
    mb_system_id = f"MB-{uuid.uuid4().hex[:8].upper()}"

    # 3. Confirm Live Pricing with Duffel
    live_offer = await flight_service.duffel_provider.confirm_price_and_policies(flight_request.offer_id)
    if "error" in live_offer:
        raise HTTPException(status_code=400, detail=live_offer["error"])
    
    priced_offer = live_offer["priced_offer"]
    
    # 4. Finalize Airline Order
    order_result = await flight_service.book_flight(
        offer_id=flight_request.offer_id, 
        travelers=flight_request.travelers, 
        selected_seats=flight_request.selected_seats
    )
    
    if "error" in order_result:
        payment_intent_id = flight_request.travelers[0].get("payment_intent_id")
        if payment_intent_id:
            try: stripe.PaymentIntent.cancel(payment_intent_id)
            except: pass
        raise HTTPException(status_code=400, detail=order_result["error"])

    # Capture funds
    payment_intent_id = flight_request.travelers[0].get("payment_intent_id")
    if payment_intent_id:
        try: stripe.PaymentIntent.capture(payment_intent_id)
        except Exception as e: print(f"Stripe capture failed: {e}")

    # --- 5. SECURE DATABASE SAVE ---
    db_booking_id = None
    if user_id: 
        try:
            try: start_date = datetime.fromisoformat(priced_offer.itineraries[0].segments[0].departure_time.replace("Z", "+00:00"))
            except: start_date = datetime.utcnow()
            
            try: end_date = datetime.fromisoformat(priced_offer.itineraries[-1].segments[-1].arrival_time.replace("Z", "+00:00"))
            except: end_date = datetime.utcnow()

            try: origin = priced_offer.itineraries[0].segments[0].departure_airport_name
            except: origin = "Origin"

            try: destination = priced_offer.itineraries[-1].segments[-1].arrival_airport_name
            except: destination = "Destination"

            try: airline_name = priced_offer.airline_name
            except: airline_name = "Unknown Airline"

            price_val = getattr(priced_offer, "price", 0.0)
            
            provider_pnr = order_result.get("booking_reference", "PENDING")
            provider_order_id = order_result.get("order_id", "UNKNOWN")

            new_booking = Booking(
                user_id=user_id, 
                booking_type=BookingType.FLIGHT,
                confirmation_code=provider_pnr,  
                # Link System ID and Provider Order ID securely!
                notes=f"System Ref: {mb_system_id} | Duffel Order: {provider_order_id}",
                provider_name="Duffel", 
                airline_provider=airline_name, 
                origin=origin,
                destination=destination,
                start_date=start_date,
                end_date=end_date,
                status=BookingStatus.CONFIRMED,
                total_price=price_val
            )
            db.add(new_booking)
            db.commit()
            db.refresh(new_booking)
            db_booking_id = new_booking.id
            print(f"\n✅ DB SAVE COMPLETE. Linked Sys ID {mb_system_id} to DB ID {db_booking_id}\n")
        except Exception as db_err:
            db.rollback()
            print(f"\n🚨 DATABASE SAVE ERROR: {str(db_err)}\n")

    final_price = getattr(priced_offer, "price", 0.0)
    return {
        "success": True,
        "booking_id": mb_system_id, # Our new unified Master ID
        "db_id": db_booking_id,
        "pnr": order_result.get("booking_reference", "PENDING"),
        "order_id": order_result.get("order_id"),
        "amount_charged": final_price,
        "currency": getattr(priced_offer, "currency", "USD"),
        "invoice": {
            "receipt_number": f"REC-{mb_system_id}-{int(datetime.utcnow().timestamp())}",
            "billing_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "payment_method": f"Stripe Card Hold Reference: {payment_intent_id}",
            "base_fare": final_price * 0.85,
            "taxes_and_fees": final_price * 0.15,
            "grand_total": final_price
        }
    }

@router.get("/orders/{order_id}")
async def get_live_duffel_order(
    order_id: str,
    current_user: User = Depends(get_current_user), 
    db: Session = Depends(get_db)
):
    try:
        token = os.getenv('DUFFEL_API_KEY')
        async with httpx.AsyncClient() as client:
            headers = {
                "Authorization": f"Bearer {token}",
                "Duffel-Version": "v2", 
                "Content-Type": "application/json"
            }
            res = await client.get(f"https://api.duffel.com/air/orders/{order_id}", headers=headers)
            
            if res.status_code == 400 and "version" in res.text.lower():
                headers["Duffel-Version"] = "beta"
                res = await client.get(f"https://api.duffel.com/air/orders/{order_id}", headers=headers)

            if res.status_code != 200:
                raise HTTPException(status_code=res.status_code, detail=f"Duffel Error: {res.text}")
                
            order_data = res.json().get("data", {})
            
            try:
                existing = db.query(Booking).filter(Booking.notes.like(f"%{order_id}%")).first()
                if not existing:
                    try:
                        f_seg = order_data.get("slices", [{}])[0].get("segments", [{}])[0]
                        l_seg = order_data.get("slices", [{}])[-1].get("segments", [{}])[-1]
                        sync_start = datetime.fromisoformat(f_seg.get("departing_at", "").replace("Z", "+00:00"))
                        sync_end = datetime.fromisoformat(l_seg.get("arriving_at", "").replace("Z", "+00:00"))
                        airline = f_seg.get("operating_carrier", {}).get("name", "Unknown Airline")
                    except:
                        sync_start, sync_end, airline = datetime.utcnow(), datetime.utcnow(), "Unknown"

                    sync_booking = Booking(
                        user_id=current_user.id,
                        booking_type=BookingType.FLIGHT,
                        confirmation_code=order_data.get("booking_reference", ""),
                        notes=f"Duffel Order ID: {order_id}. Auto-Synced.",
                        provider_name="Duffel", 
                        airline_provider=airline, 
                        origin=f_seg.get("origin", {}).get("name", "Unknown"), 
                        destination=l_seg.get("destination", {}).get("name", "Unknown"), 
                        start_date=sync_start,
                        end_date=sync_end,
                        status=BookingStatus.CONFIRMED,
                        total_price=float(order_data.get("total_amount", 0.0))
                    )
                    db.add(sync_booking)
                    db.commit()
            except Exception as e:
                db.rollback()

            return order_data
            
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))