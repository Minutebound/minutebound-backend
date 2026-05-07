import pytest
from unittest.mock import patch, AsyncMock
import app.api.v1.endpoints.users as users
from app.main import app
from app.api.v1.deps import get_current_user

pytestmark = pytest.mark.asyncio

@pytest.mark.regression
class Test_Users():
    api_path = "/api/v1/users/me"

    def test_get_profiles(self, auth_client):
        response = auth_client.get(self.api_path)
    
        assert response.status_code == 200
        data = response.json()
        assert data["full_name"] == "Test User"
        assert data["email"] == "test@test.com"

    def test_get_profile_unauthenticated(self, auth_client):
        app.dependency_overrides.pop(get_current_user, None)
        response = auth_client.get(self.api_path)

        assert response.status_code == 401

    async def test_update_profile(self, auth_client):
        response = auth_client.put(
            self.api_path,
            data= {"full_name": "Updated User"}
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Profile updated successfully"
    
    async def test_empty_update(self, auth_client):
        response = auth_client.put(
            self.api_path,
            data= {}
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "No fields provided to update"
