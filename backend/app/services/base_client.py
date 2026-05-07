import httpx
import time
from typing import Any, Dict, Optional
from app.core.config import settings

class BaseAmadeusClient:
    def __init__(self):
        self.base_url = "https://api.amadeus.com"
        self.client_id = settings.AMADEUS_CLIENT_ID
        self.client_secret = settings.AMADEUS_CLIENT_SECRET
        self.token = None
        self.token_expiry = 0

    async def get_token(self):
        """Fetches and caches the OAuth2 token for Amadeus"""
        if self.token and time.time() < self.token_expiry:
            return self.token

        url = f"{self.base_url}/v1/security/oauth2/token"
        headers = {"Content-Type": "application/x-www-form-urlencoded"}
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers, data=data)
            if response.status_code != 200:
                print(f"Auth Failed: {response.text}")
                return None
            result = response.json()
            self.token = result["access_token"]
            self.token_expiry = time.time() + result["expires_in"] - 10
            return self.token

    async def _make_request(
        self, 
        method: str, 
        endpoint: str, 
        params: Optional[Dict[str, Any]] = None, 
        headers: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None
    ) -> Any:
        """🌟 ADDED: Generic request helper that works with Redis Caching"""
        url = f"{self.base_url}{endpoint}"
        
        token = await self.get_token()
        if not headers:
            headers = {}
        headers["Authorization"] = f"Bearer {token}"

        async with httpx.AsyncClient(timeout=30.0) as client:
            try:
                response = await client.request(
                    method=method,
                    url=url,
                    params=params,
                    headers=headers,
                    json=json_data
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as e:
                return {"error": f"API Error: {e.response.status_code}", "detail": e.response.text}
            except Exception as e:
                return {"error": f"Connection Error: {str(e)}"}