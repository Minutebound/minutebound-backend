from fastapi import APIRouter, HTTPException, Query
from typing import List, Optional
from app.services.flight_service import flight_service
from app.schemas.flight import FlightOffer, PriceConfirmRequest, FlightBookRequest, PaymentIntentRequest
from fastapi_cache.decorator import cache

router = APIRouter()

@router.get("/search", response_model=List[FlightOffer])
@cache(expire=86400) 
async def search_flights(
    origin: str,
    destination: str,
    date: str,
    return_date: Optional[str] = None, # <-- Ensure this is Optional
    adults: int = 1,
    children: int = 0,
    travel_class: str = "ECONOMY"
):
    """
    Search for flights. Supports one-way if return_date is omitted.
    """
    results = await flight_service.search_flights(
        origin=origin,
        destination=destination,
        date=date,
        return_date=return_date,
        adults=adults,
        children=children,
        travel_class=travel_class
    )
    
    if isinstance(results, dict) and "error" in results:
        raise HTTPException(status_code=400, detail=results["error"])
        
    return results

@router.post("/price")
async def confirm_flight_price(request: PriceConfirmRequest):
    """
    Step 2 of Booking Flow: Confirm the price is still valid and fetch cancellation policies.
    """
    result = await flight_service.confirm_price(request.flight_offer)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

@router.post("/book")
async def book_flight(request: FlightBookRequest):
    """
    Step 3 of Booking Flow: Create the actual flight order/booking in Amadeus.
    """
    result = await flight_service.book_flight(request.priced_offer, request.travelers)
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

@router.post("/create-payment-intent")
async def create_payment_intent(request: PaymentIntentRequest):
    """
    Creates a secure Stripe Payment Intent for the frontend to capture.
    """
    try:
        # Stripe expects amounts in the smallest currency unit (e.g., cents)
        amount_in_cents = int(request.amount * 100)
        
        intent = stripe.PaymentIntent.create(
            amount=amount_in_cents,
            currency=request.currency.lower(),
            # For travel, you often 'authorize' first and 'capture' later, 
            # but for this MVP, we will use automatic capture.
            automatic_payment_methods={"enabled": True},
        )
        return {"client_secret": intent.client_secret}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))