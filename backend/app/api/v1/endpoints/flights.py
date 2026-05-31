import stripe
import os
import httpx
from fastapi import APIRouter, HTTPException, Depends, Query
from typing import List, Optional
from sqlalchemy.orm import Session
from datetime import datetime

from app.api.v1.deps import get_current_user
from app.db.database import get_db
from app.db.models import User, Booking
from app.core.enums import BookingType, BookingStatus
from app.services.flight_service import flight_service
from app.schemas.flight import (
    FlightOffer, PriceConfirmRequest, FlightBookRequest, 
    PaymentIntentRequest, PriceConfirmResponse
)

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
async def create_payment_intent(request: PaymentIntentRequest, current_user: User = Depends(get_current_user)):
    try:
        amount_in_cents = int(request.amount * 100)
        intent = stripe.PaymentIntent.create(
            amount=amount_in_cents, currency=request.currency.lower(), capture_method="manual",
            metadata={"user_id": current_user.id, "user_email": current_user.email}
        )
        return {"client_secret": intent.client_secret, "intent_id": intent.id}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/book")
async def book_flight(
    request: FlightBookRequest, 
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    live_offer = await flight_service.duffel_provider.confirm_price_and_policies(request.offer_id)
    if "error" in live_offer:
        raise HTTPException(status_code=400, detail=live_offer["error"])
    
    priced_offer = live_offer["priced_offer"]
    
    try:
        start_date_str = priced_offer.itineraries[0].segments[0].departure_time
        end_date_str = priced_offer.itineraries[-1].segments[-1].arrival_time
        start_date = datetime.fromisoformat(start_date_str.replace("Z", "+00:00"))
        end_date = datetime.fromisoformat(end_date_str.replace("Z", "+00:00"))
    except Exception:
        start_date = datetime.utcnow()
        end_date = datetime.utcnow()

    order_result = await flight_service.book_flight(
        offer_id=request.offer_id, travelers=request.travelers, selected_seats=request.selected_seats
    )
    
    if "error" in order_result:
        payment_intent_id = request.travelers[0].get("payment_intent_id")
        if payment_intent_id:
            try: stripe.PaymentIntent.cancel(payment_intent_id)
            except: pass
        raise HTTPException(status_code=400, detail=order_result["error"])

    payment_intent_id = request.travelers[0].get("payment_intent_id")
    if payment_intent_id:
        try: stripe.PaymentIntent.capture(payment_intent_id)
        except Exception as e: print(f"Stripe capture failed: {e}")

    # --- SAFE DATABASE SAVE ---
    booking_id = None
    try:
        new_booking = Booking(
            user_id=current_user.id,
            booking_type=BookingType.FLIGHT,
            confirmation_code=order_result["booking_reference"],  
            notes=f"Duffel Order ID: {order_result['order_id']}. Cabin Class: {priced_offer.cabin_class.upper()}.",
            provider_name="Duffel", 
            airline_provider=priced_offer.airline_name, 
            origin=priced_offer.itineraries[0].segments[0].departure_airport_name, # <--- ADDED
            destination=priced_offer.itineraries[-1].segments[-1].arrival_airport_name, # <--- ADDED
            start_date=start_date,
            end_date=end_date,
            status=BookingStatus.CONFIRMED,
            total_price=priced_offer.price
        )
        db.add(new_booking)
        db.commit()
        db.refresh(new_booking)
        booking_id = new_booking.id
        print(f"\n✅ SUCCESSFULLY SAVED BOOKING TO DATABASE: ID {booking_id}\n")
    except Exception as db_err:
        db.rollback()
        # This will print the EXACT reason the DB failed in your terminal!
        print(f"\n🚨 DATABASE SAVE ERROR: {str(db_err)}\n(Did you wipe your Docker volume to apply the 'airline_provider' schema update?)\n")

    return {
        "success": True,
        "booking_id": booking_id,
        "pnr": order_result["booking_reference"],
        "order_id": order_result["order_id"],
        "amount_charged": priced_offer.price,
        "currency": priced_offer.currency,
        "invoice": {
            "receipt_number": f"REC-{booking_id or 'TEMP'}-{int(datetime.utcnow().timestamp())}",
            "billing_date": datetime.utcnow().strftime("%Y-%m-%d"),
            "payment_method": f"Stripe Card Hold Reference: {payment_intent_id}",
            "base_fare": priced_offer.price * 0.85,
            "taxes_and_fees": priced_offer.price * 0.15,
            "grand_total": priced_offer.price
        }
    }

@router.get("/orders/{order_id}")
async def get_live_duffel_order(
    order_id: str,
    current_user: User = Depends(get_current_user), # Requires user to sync
    db: Session = Depends(get_db)
):
    """
    Fetches the live order from Duffel AND auto-syncs it to the DB if missing.
    """
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
            
            # --- DATABASE AUTO-SYNC ---
            try:
                # Check if we already have it
                existing = db.query(Booking).filter(Booking.notes.like(f"%{order_id}%")).first()
                if not existing:
                    print(f"🔄 Order {order_id} not found in DB. Auto-syncing now...")
                    
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
                    origin=f_seg.get("origin", {}).get("name", "Unknown"), # <--- ADDED
                    destination=l_seg.get("destination", {}).get("name", "Unknown"), # <--- ADDED
                    start_date=sync_start,
                    end_date=sync_end,
                    status=BookingStatus.CONFIRMED,
                    total_price=float(order_data.get("total_amount", 0.0))
                )
                    db.add(sync_booking)
                    db.commit()
                    print(f"✅ Auto-sync complete for {order_id}!")
            except Exception as e:
                db.rollback()
                print(f"🚨 AUTO-SYNC FAILED: {str(e)}")

            return order_data
            
    except HTTPException: raise
    except Exception as e: raise HTTPException(status_code=500, detail=str(e))