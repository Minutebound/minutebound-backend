import json
import secrets
from fastapi import APIRouter, Depends, Response, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Any
from fpdf import FPDF
from datetime import datetime

from app.db.database import get_db
from app.db.models import User, SavedItinerary, VisibilityEnum
from app.api.v1.deps import get_current_user

from app.schemas.itinerary import (
    ItineraryGenerateRequest, 
    ItineraryCreate, 
    ItineraryResponse, 
    UpdateVisibilityRequest, 
    ShareItineraryEmailRequest
)
import smtplib
from email.message import EmailMessage
from app.core.config import settings

router = APIRouter()

def sanitize_text(text) -> str:
    if text is None:
        return ""
    clean_text = str(text).replace("°", " deg").replace("\u00b0", " deg").replace("\u2013", "-").replace("\u2014", "-")
    return clean_text.encode('latin-1', 'ignore').decode('latin-1')

def safe_float(value) -> float:
    if value is None: return 0.0
    try:
        if isinstance(value, dict):
            val = value.get('total') or value.get('amount') or 0
            return safe_float(val)
        clean_val = str(value).replace('$', '').replace(',', '').strip()
        if not clean_val or clean_val.upper() == "N/A": return 0.0
        return float(clean_val)
    except (ValueError, TypeError): return 0.0

def format_time(time_str: str) -> str:
    if not time_str: return ""
    try:
        dt = datetime.fromisoformat(time_str.replace('Z', '+00:00'))
        return dt.strftime("%I:%M %p")
    except: return time_str

def format_date(date_str: str) -> str:
    if not date_str: return ""
    try:
        dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
        return dt.strftime("%b %d")
    except: return date_str

def build_pdf_content(payload_dict: dict) -> bytes:
    pdf = FPDF()
    pdf.add_page()
    
    pdf.set_font("helvetica", "B", 22)
    pdf.cell(0, 12, "Your Custom Itinerary", align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_font("helvetica", "B", 14)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 8, sanitize_text(payload_dict.get("destination", "Trip")), align="C", new_x="LMARGIN", new_y="NEXT")
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("helvetica", "I", 11)
    pdf.cell(0, 8, f"Prepared for: {sanitize_text(payload_dict.get('username'))} | {payload_dict.get('check_in_date')} - {payload_dict.get('check_out_date')}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.ln(5)

    total_cost = 0.0
    flight = payload_dict.get("flight")
    drive = payload_dict.get("drive")
    if flight: total_cost += safe_float(flight.get('price'))
    elif drive: total_cost += safe_float(drive.get('fuelEstimate'))
        
    hotel = payload_dict.get("hotel")
    if hotel:
        hotel_price = hotel.get('price') or hotel.get('offerDetails', {}).get('price')
        total_cost += safe_float(hotel_price)
    
    pdf.set_font("helvetica", "B", 13)
    pdf.set_text_color(34, 197, 94) 
    pdf.cell(0, 10, f"TOTAL ESTIMATED COST: ${total_cost:,.2f}", align="C", new_x="LMARGIN", new_y="NEXT")
    pdf.set_text_color(0, 0, 0)
    pdf.ln(5)

    def draw_section_header(title):
        pdf.set_font("helvetica", "B", 13)
        pdf.set_fill_color(245, 245, 245)
        pdf.cell(0, 10, f"  {title}", fill=True, new_x="LMARGIN", new_y="NEXT")
        pdf.ln(2)

    weather = payload_dict.get("weather")
    if weather:
        draw_section_header("Expected Weather")
        pdf.set_font("helvetica", "", 11)
        summary = weather.get("overall_summary") or weather.get("error", "Weather info available.")
        pdf.multi_cell(0, 7, f"  {sanitize_text(summary)}")
        pdf.ln(4)

    if flight or drive:
        draw_section_header("Transportation")
        if flight:
            airline = sanitize_text(flight.get('airline_name', 'Flight'))
            price = safe_float(flight.get('price'))
            pdf.set_font("helvetica", "B", 11)
            pdf.cell(0, 7, f"  {airline} (Total: ${price:,.2f})", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", "", 10)
            for i, itin in enumerate(flight.get("itineraries", [])):
                bound = "Outbound" if i == 0 else "Return"
                pdf.set_font("helvetica", "I", 9)
                pdf.cell(0, 6, f"    --- {bound} ---", new_x="LMARGIN", new_y="NEXT")
                pdf.set_font("helvetica", "", 9)
                for seg in itin.get("segments", []):
                    dep_name = sanitize_text(seg.get('departure_airport_name') or seg.get('departure_airport', ''))
                    arr_name = sanitize_text(seg.get('arrival_airport_name') or seg.get('arrival_airport', ''))
                    dep_code = seg.get('departure_airport', '')
                    arr_code = seg.get('arrival_airport', '')
                    dep_time = format_time(seg.get('departure_time'))
                    arr_time = format_time(seg.get('arrival_time'))
                    pdf.cell(0, 6, f"    {dep_name} ({dep_code}) [{dep_time}] -> {arr_name} ({arr_code}) [{arr_time}]", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)
        if drive:
            pdf.set_font("helvetica", "B", 11)
            pdf.cell(0, 7, "  Road Trip Journey", new_x="LMARGIN", new_y="NEXT")
            pdf.set_font("helvetica", "", 10)
            pdf.cell(0, 6, f"    Duration: {drive.get('duration')} | Distance: {drive.get('distance')}", new_x="LMARGIN", new_y="NEXT")
            pdf.cell(0, 6, f"    Estimated Fuel Cost: ${safe_float(drive.get('fuelEstimate')):,.2f}", new_x="LMARGIN", new_y="NEXT")
            pdf.ln(3)

    if hotel:
        draw_section_header("Accommodation")
        pdf.set_font("helvetica", "B", 11)
        pdf.cell(0, 7, f"  {sanitize_text(hotel.get('name'))}", new_x="LMARGIN", new_y="NEXT")
        pdf.set_font("helvetica", "", 10)
        addr = ", ".join(hotel.get("address", {}).get("lines", []))
        if addr: pdf.cell(0, 6, f"    Address: {sanitize_text(addr)}", new_x="LMARGIN", new_y="NEXT")
        hp = hotel.get('price') or hotel.get('offerDetails', {}).get('price')
        pdf.cell(0, 6, f"    Total Price: ${safe_float(hp):,.2f}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    attractions = payload_dict.get("attractions", [])
    if attractions:
        draw_section_header("Planned Attractions")
        pdf.set_font("helvetica", "", 11)
        for attr in attractions:
            pdf.cell(0, 7, f"   - {sanitize_text(attr.get('name'))}", new_x="LMARGIN", new_y="NEXT")
        pdf.ln(4)

    # UPDATED SECTION: changed activities to tours
    tours = payload_dict.get("tours", [])
    if tours:
        draw_section_header("Tours & Experiences")
        pdf.set_font("helvetica", "", 11)
        for act in tours:
            name = act.get('name') or act.get('title')
            pdf.cell(0, 7, f"   - {sanitize_text(name)}", new_x="LMARGIN", new_y="NEXT")

    return bytes(pdf.output())

def send_background_trip_email(user_email: str, user_name: str, destination: str, trip_data: dict):
    try:
        pdf_bytes = build_pdf_content(trip_data)
        msg = EmailMessage()
        msg['Subject'] = f"Your minutebound Itinerary: {destination}!"
        msg['From'] = settings.FROM_EMAIL
        msg['To'] = user_email
        email_body = f"Hi {user_name},\n\nGreat news! Your trip to {destination} has been successfully saved.\n\nAttached is your custom PDF itinerary.\n\nSafe travels!\nThe minutebound Team"
        msg.set_content(email_body)
        msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=f"{destination}_Itinerary.pdf")
        
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
            server.send_message(msg)
    except Exception as e:
        print(f"Background email error: {e}")

@router.post("/generate-pdf")
async def generate_itinerary_pdf(payload: ItineraryGenerateRequest):
    try:
        pdf_bytes = build_pdf_content(payload.model_dump())
        safe_name = "".join(x for x in payload.destination if x.isalnum()) or "Itinerary"
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}_Itinerary.pdf"'}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"PDF Generation Failed: {str(e)}")

@router.post("/save", response_model=ItineraryResponse)
async def save_itinerary(
    payload: ItineraryCreate, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db), 
    current_user: User = Depends(get_current_user)
):
    existing = db.query(SavedItinerary).filter(SavedItinerary.user_id == current_user.id).all()
    for itinerary in existing:
        if itinerary.data == payload.data: 
            return itinerary 
            
    token = secrets.token_urlsafe(16) if payload.visibility != VisibilityEnum.PRIVATE else None

    new_itinerary = SavedItinerary(
        destination=payload.destination, 
        data=payload.data, 
        visibility=payload.visibility,
        share_token=token,
        user_id=current_user.id
    )
    db.add(new_itinerary)
    db.commit()
    db.refresh(new_itinerary)

    user_full_name = f"{current_user.first_name} {current_user.last_name}".strip()
    background_tasks.add_task(
        send_background_trip_email,
        user_email=current_user.email,
        user_name=user_full_name,
        destination=new_itinerary.destination,
        trip_data=payload.data
    )

    return new_itinerary

@router.get("/me", response_model=List[ItineraryResponse])
async def get_my_itineraries(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    return db.query(SavedItinerary).filter(SavedItinerary.user_id == current_user.id).all()

@router.delete("/{itinerary_id}")
async def delete_itinerary(itinerary_id: str, db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    itinerary = db.query(SavedItinerary).filter(SavedItinerary.id == itinerary_id, SavedItinerary.user_id == current_user.id).first()
    if not itinerary: 
        raise HTTPException(status_code=404, detail="Itinerary not found")
    db.delete(itinerary)
    db.commit()
    return {"message": "Itinerary deleted successfully"}

@router.patch("/{itinerary_id}/visibility", response_model=ItineraryResponse)
async def update_itinerary_visibility(
    itinerary_id: str,
    payload: UpdateVisibilityRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    itinerary = db.query(SavedItinerary).filter(SavedItinerary.id == itinerary_id, SavedItinerary.user_id == current_user.id).first()
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")
    
    itinerary.visibility = payload.visibility
    
    if payload.visibility != VisibilityEnum.PRIVATE and not itinerary.share_token:
        itinerary.share_token = secrets.token_urlsafe(16)
        
    db.commit()
    db.refresh(itinerary)
    return itinerary

@router.get("/shared/{share_token}", response_model=ItineraryResponse)
async def get_shared_itinerary(share_token: str, db: Session = Depends(get_db)):
    itinerary = db.query(SavedItinerary).filter(SavedItinerary.share_token == share_token).first()
    if not itinerary:
        raise HTTPException(status_code=404, detail="Shared itinerary not found")
    
    if itinerary.visibility == VisibilityEnum.PRIVATE:
        raise HTTPException(status_code=403, detail="This itinerary is no longer public")
        
    return itinerary

@router.post("/{itinerary_id}/share-email")
async def email_shared_itinerary(
    itinerary_id: str,
    payload: ShareItineraryEmailRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    itinerary = db.query(SavedItinerary).filter(SavedItinerary.id == itinerary_id, SavedItinerary.user_id == current_user.id).first()
    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found")

    def send_friend_email():
        try:
            pdf_bytes = build_pdf_content(itinerary.data)
            msg = EmailMessage()
            msg['Subject'] = f"{current_user.first_name} shared an itinerary to {itinerary.destination} with you!"
            msg['From'] = settings.FROM_EMAIL
            msg['To'] = payload.email
            
            body = f"Hi there,\n\n{current_user.first_name} {current_user.last_name} thought you'd like to see their itinerary for {itinerary.destination}.\n"
            if payload.message:
                body += f"\nThey included a message:\n\"{payload.message}\"\n"
            
            if itinerary.visibility != VisibilityEnum.PRIVATE and itinerary.share_token:
                frontend_url = getattr(settings, 'FRONTEND_URL', 'http://localhost:3000')
                body += f"\nYou can view the full interactive trip online here:\n{frontend_url}/shared/{itinerary.share_token}\n"
                
            body += "\nSafe travels!\nThe minutebound Team"
            msg.set_content(body)
            msg.add_attachment(pdf_bytes, maintype='application', subtype='pdf', filename=f"{itinerary.destination}_Itinerary.pdf")
            
            with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
                server.starttls()
                server.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
                server.send_message(msg)
        except Exception as e:
            print(f"Share email error: {e}")

    background_tasks.add_task(send_friend_email)
    return {"message": f"Itinerary sent to {payload.email}"}