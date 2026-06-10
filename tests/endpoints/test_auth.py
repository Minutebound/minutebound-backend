import pytest
import app.api.v1.endpoints.auth as auth
from app.main import app
from app.db.models import User
from app.schemas.auth import Token, UserCreate, UserLogin, ForgotPassword, ResetPassword

@pytest.mark.regression
class TestAuth():
    api_path = "/api/v1/auth"
    api_path_signup = api_path + "/signup"
    api_path_login = api_path + "/login"
    api_path_forgot_password = api_path + "/forgot-password"
    api_path_reset_password = api_path + "/reset-password"

    @pytest.mark.smoke
    async def test_new_user_signup(self, auth_client, db):
        new_user_email = "newuser@test.com"
        new_user_password = "password123"
        new_user_full_name = "New User"

        response = auth_client.post(
            self.api_path_signup,
            json={
                "email": new_user_email,
                "password": new_user_password,
                "full_name": new_user_full_name
            }
        )

        assert response.status_code == 200
        assert "access_token" in response.json()

        new_user = db.query(User).filter(User.email == "newuser@test.com").first()
        assert new_user is not None
        assert new_user.full_name == new_user_full_name
        assert new_user.hashed_password != new_user_password

    @pytest.mark.smoke
    async def test_duplicate_user_signup(self, auth_client):
        response = auth_client.post(
            self.api_path_signup,
            json={
                "email": "test@test.com",
                "password": "password123",
                "full_name": "Duplicate User"
            }
        )

        assert response.status_code == 400
        assert response.json()['detail'] == "Email already registered"

    async def test_signup_invalid_email(self, auth_client):
        response = auth_client.post(
            self.api_path_signup,
            json={
                "email": "not-an-email",
                "password": "password123",
                "full_name": "Bad Email User"
            }
        )

        assert response.status_code == 422

    async def test_signup_missing_fields(self, auth_client):
        response = auth_client.post(
            self.api_path_signup,
            json={"email": "incomplete@test.com"}
        )

        assert response.status_code == 422

    async def test_valid_user_login(self, auth_client):
        response = auth_client.post(
            self.api_path_login,
            json={
                "email": "test@test.com",
                "password": "password"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["email"] == "test@test.com"

    async def test_login_wrong_password(self, auth_client):
        response = auth_client.post(
            self.api_path_login,
            json={
                "email": "test@test.com",
                "password": "wrongpassword"
            }
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Incorrect email or password"

    async def test_login_nonexistent_user(self, auth_client):
        response = auth_client.post(
            self.api_path_login,
            json={
                "email": "doesnotexist@test.com",
                "password": "password"
            }
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Incorrect email or password"

    async def test_login_invalid_email_format(self, auth_client):
        response = auth_client.post(
            self.api_path_login,
            json={
                "email": "not-an-email",
                "password": "password"
            }
        )

        assert response.status_code == 422

    @pytest.mark.smoke
    async def test_forgot_password_existing_user(self, auth_client, db):
        response = auth_client.post(
            self.api_path_forgot_password,
            json={"email": "test@test.com"}
        )

        assert response.status_code == 200
        assert response.json()["message"] == "If that email is registered, a reset code has been sent."

        # Verify the reset code was actually saved on the user
        user = db.query(User).filter(User.email == "test@test.com").first()
        assert user.reset_code is not None
        assert len(user.reset_code) == 6
        assert user.reset_code_expires is not None

    async def test_forgot_password_nonexistent_user(self, auth_client):
        response = auth_client.post(
            self.api_path_forgot_password,
            json={"email": "doesnotexist@test.com"}
        )

        # Should return generic success message to prevent email enumeration
        assert response.status_code == 200
        assert response.json()["message"] == "If that email is registered, a reset code has been sent."

    @pytest.mark.smoke
    async def test_reset_password_pass(self, auth_client, db):
        # First, trigger forgot-password to generate a code
        auth_client.post(
            self.api_path_forgot_password,
            json={"email": "test@test.com"}
        )

        user = db.query(User).filter(User.email == "test@test.com").first()
        reset_code = user.reset_code
        old_hash = user.hashed_password

        response = auth_client.post(
            self.api_path_reset_password,
            json={
                "email": "test@test.com",
                "code": reset_code,
                "new_password": "newpassword123"
            }
        )

        assert response.status_code == 200
        assert response.json()["message"] == "Password reset successfully. You can now log in."

        # Verify the password was actually changed and reset code cleared
        db.refresh(user)
        assert user.hashed_password != old_hash
        assert user.reset_code is None
        assert user.reset_code_expires is None

    async def test_reset_password_invalid_code(self, auth_client, db):
        auth_client.post(
            self.api_path_forgot_password,
            json={"email": "test@test.com"}
        )

        response = auth_client.post(
            self.api_path_reset_password,
            json={
                "email": "test@test.com",
                "code": "000000",
                "new_password": "newpassword123"
            }
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid email or verification code."

    async def test_reset_password_nonexistent_user(self, auth_client):
        response = auth_client.post(
            self.api_path_reset_password,
            json={
                "email": "doesnotexist@test.com",
                "code": "123456",
                "new_password": "newpassword123"
            }
        )

        assert response.status_code == 400
        assert response.json()["detail"] == "Invalid email or verification code."
