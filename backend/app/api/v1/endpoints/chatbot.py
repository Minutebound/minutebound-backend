from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import os
from openai import OpenAI
from app.core.config import settings

router = APIRouter()
client = OpenAI(api_key=settings.OPENAI_API_KEY)

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    context: Optional[str] = None  

@router.post("/")
async def chat_with_ai(request: ChatRequest):
    try:
        system_content = (
            "You are WanderBot, an expert travel assistant for the WanderPlan app. "
            "Help users plan trips, suggest local attractions, give weather advice, "
            "and create day-by-day itineraries. Keep responses concise and engaging."
        )
        
        if request.context:
            system_content += f"\n\nCurrent Context: {request.context}"
            
        system_prompt = {"role": "system", "content": system_content}
        
        api_messages = [system_prompt] + [{"role": m.role, "content": m.content} for m in request.messages]
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=api_messages,
            temperature=0.7
        )
        
        return {"reply": response.choices[0].message.content}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))