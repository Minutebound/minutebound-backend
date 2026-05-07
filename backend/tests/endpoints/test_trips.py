import pytest
from unittest.mock import patch, MagicMock
from app.main import app
from app.api.v1.deps import get_current_user

pytestmark = pytest.mark.asyncio

@pytest.mark.regression
class Test_Trips_PDF():
    api_path = "/api/v1/trips"

    default_payload = {
        "username": "Test User",
        "destination": "New York",
        "check_in_date": "2026-05-01",
        "check_out_date": "2026-05-05",
    }

    async def test_generate_pdf_pass(self, client):
        response = client.post(
            f"{self.api_path}/generate-pdf",
            json=self.default_payload
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"
        assert "Content-Disposition" in response.headers

    async def test_generate_pdf_missing_required_fields(self, client):
        response = client.post(
            f"{self.api_path}/generate-pdf",
            json={"username": "Test User"}
        )

        assert response.status_code == 422

    async def test_generate_pdf_empty_body(self, client):
        response = client.post(
            f"{self.api_path}/generate-pdf",
            json={}
        )

        assert response.status_code == 422

    async def test_generate_pdf_with_flight(self, client):
        payload = {
            **self.default_payload,
            "flight": {
                "airline_name": "Test Air",
                "price": 350.00,
                "itineraries": []
            }
        }
        response = client.post(
            f"{self.api_path}/generate-pdf",
            json=payload
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    async def test_generate_pdf_with_hotel(self, client):
        payload = {
            **self.default_payload,
            "hotel": {
                "name": "Test Hotel",
                "price": 200.00,
                "address": {"lines": ["123 Main St"]}
            }
        }
        response = client.post(
            f"{self.api_path}/generate-pdf",
            json=payload
        )

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/pdf"

    async def test_share_pdf_missing_email(self, client):
        response = client.post(
            f"{self.api_path}/share-pdf",
            json=self.default_payload
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Email is required"

    @patch("smtplib.SMTP")
    async def test_share_pdf_pass(self, mock_smtp, client):
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__ = MagicMock(return_value=mock_server)
        mock_smtp.return_value.__exit__ = MagicMock(return_value=False)

        payload = {**self.default_payload, "email": "test@test.com"}
        response = client.post(
            f"{self.api_path}/share-pdf",
            json=payload
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Email sent successfully"


@pytest.mark.regression
class Test_Trips_DB():
    api_path = "/api/v1/trips"

    default_trip = {
        "destination": "New York",
        "check_in_date": "2026-05-01",
        "check_out_date": "2026-05-05"
    }

    async def test_save_trip(self, auth_client):
        response = auth_client.post(
            f"{self.api_path}/save",
            json=self.default_trip
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Trip saved successfully"

    async def test_save_duplicate_trip(self, auth_client):
        auth_client.post(f"{self.api_path}/save", json=self.default_trip)
        response = auth_client.post(f"{self.api_path}/save", json=self.default_trip)

        assert response.status_code == 200
        assert response.json()["message"] == "Trip already saved!"

    async def test_get_my_trips(self, auth_client):
        auth_client.post(f"{self.api_path}/save", json=self.default_trip)
        response = auth_client.get(f"{self.api_path}/me")

        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["destination"] == "New York"
        assert "id" in data[0]
        assert "data" in data[0]

    async def test_get_my_trips_empty(self, auth_client):
        response = auth_client.get(f"{self.api_path}/me")

        assert response.status_code == 200
        assert response.json() == []

    async def test_delete_trip(self, auth_client):
        auth_client.post(f"{self.api_path}/save", json=self.default_trip)

        trips = auth_client.get(f"{self.api_path}/me").json()
        trip_id = trips[0]["id"]

        response = auth_client.delete(f"{self.api_path}/{trip_id}")

        assert response.status_code == 200
        assert response.json()["message"] == "Trip deleted successfully"

        remaining = auth_client.get(f"{self.api_path}/me").json()
        assert len(remaining) == 0

    async def test_delete_trip_not_found(self, auth_client):
        response = auth_client.delete(f"{self.api_path}/99999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Trip not found"

    async def test_save_trip_unauthenticated(self, auth_client):
        app.dependency_overrides.pop(get_current_user, None)
        response = auth_client.post(
            f"{self.api_path}/save",
            json=self.default_trip
        )

        assert response.status_code == 401

    async def test_get_my_trips_unauthenticated(self, auth_client):
        app.dependency_overrides.pop(get_current_user, None)
        response = auth_client.get(f"{self.api_path}/me")

        assert response.status_code == 401

    async def test_delete_trip_unauthenticated(self, auth_client):
        app.dependency_overrides.pop(get_current_user, None)
        response = auth_client.delete(f"{self.api_path}/1")

        assert response.status_code == 401
