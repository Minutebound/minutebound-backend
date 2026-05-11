from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from app.providers.llm.openai_provider import OpenAILLMProvider
from app.providers.base import ProviderFallbackManager

router = APIRouter()
llm_providers = [OpenAILLMProvider()] 

class Message(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    messages: List[Message]
    context: Optional[str] = None  

@router.post("/")
async def chat_with_ai(request: ChatRequest):
    formatted_messages = [{"role": m.role, "content": m.content} for m in request.messages]
    
    result = await ProviderFallbackManager.execute(
        llm_providers, 
        "generate_chat_reply", 
        messages=formatted_messages, 
        context=request.context
    )
    
    if isinstance(result, dict) and "error" in result:
        raise HTTPException(status_code=500, detail=result["error"])
        
    return {"reply": result}