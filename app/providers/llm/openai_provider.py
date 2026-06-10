from openai import AsyncOpenAI
from app.core.config import settings
from typing import List, Dict, Optional

class OpenAILLMProvider:
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"

    async def generate_chat_reply(self, messages: List[Dict[str, str]], context: Optional[str] = None) -> str:
        system_content = (
            "You are WanderBot, an expert travel assistant for the minutebound app. "
            "Help users plan trips, suggest local attractions, give weather advice, "
            "and create day-by-day itineraries. Keep responses concise and engaging."
        )
        if context:
            system_content += f"\n\nCurrent Context: {context}"
            
        api_messages = [{"role": "system", "content": system_content}] + messages
        
        response = await self.client.chat.completions.create(
            model=self.model,
            messages=api_messages,
            temperature=0.7
        )
        return response.choices[0].message.content