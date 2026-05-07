import pytest
from unittest.mock import patch, MagicMock
from app.api.v1.endpoints.chatbot import *

pytestmark = pytest.mark.asyncio


def _mock_openai_response(content="Hello traveler!"):
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = content
    return mock_response

@pytest.mark.regression
class TestChatbot():
    api_path = "/api/v1/chatbot/"

    # --- Successful chat completions (mocked OpenAI) ---
    chat_success_param = ("payload, reply_content",
                        [
                            pytest.param(
                                {"messages": [{"role": "user", "content": "Plan a trip to Tokyo"}]},
                                "Sure! Here's a Tokyo itinerary...",
                                id="simple_user_message",
                            ),
                            pytest.param(
                                {
                                    "messages": [{"role": "user", "content": "Suggest activities"}],
                                    "context": "User is looking at trips to Paris",
                                },
                                "Here are some Paris activities...",
                                id="with_context",
                            ),
                            pytest.param(
                                {
                                    "messages": [
                                        {"role": "user", "content": "Hi"},
                                        {"role": "assistant", "content": "Hello!"},
                                        {"role": "user", "content": "Weather in NYC?"},
                                    ]
                                },
                                "NYC weather is usually...",
                                id="multi_turn_conversation",
                            ),
                        ])

    @pytest.mark.parametrize(*chat_success_param)
    async def test_chat_success(self, client, payload, reply_content):
        with patch("app.api.v1.endpoints.chatbot.client.chat.completions.create") as mock_create:
            mock_create.return_value = _mock_openai_response(reply_content)

            response = client.post(self.api_path, json=payload)

            assert response.status_code == 200
            assert response.json() == {"reply": reply_content}

            # Verify system prompt + context handling
            call_kwargs = mock_create.call_args.kwargs
            api_messages = call_kwargs["messages"]
            assert api_messages[0]["role"] == "system"
            assert "WanderBot" in api_messages[0]["content"]
            if payload.get("context"):
                assert payload["context"] in api_messages[0]["content"]
            assert len(api_messages) == 1 + len(payload["messages"])

    # --- Validation (422) errors ---
    validation_error_param = ("payload",
                        [
                            pytest.param({}, id="empty_body"),
                            pytest.param({"context": "hi"}, id="missing_messages"),
                            pytest.param({"messages": [{"role": "user"}]}, id="message_missing_content"),
                            pytest.param({"messages": [{"content": "hi"}]}, id="message_missing_role"),
                            pytest.param({"messages": "not-a-list"}, id="messages_wrong_type"),
                        ])

    @pytest.mark.parametrize(*validation_error_param)
    async def test_validation_errors(self, client, payload):
        response = client.post(self.api_path, json=payload)
        assert response.status_code == 422

    # --- Upstream OpenAI failure → 500 ---
    async def test_openai_api_failure(self, client):
        with patch("app.api.v1.endpoints.chatbot.client.chat.completions.create") as mock_create:
            mock_create.side_effect = Exception("OpenAI API down")

            response = client.post(
                self.api_path,
                json={"messages": [{"role": "user", "content": "hello"}]},
            )

            assert response.status_code == 500
            assert response.json()["detail"] == "OpenAI API down"

    async def test_empty_messages_list(self, client):
        """Empty messages list is schema-valid; should still hit OpenAI with just system prompt."""
        with patch("app.api.v1.endpoints.chatbot.client.chat.completions.create") as mock_create:
            mock_create.return_value = _mock_openai_response("Hi! How can I help?")

            response = client.post(self.api_path, json={"messages": []})

            assert response.status_code == 200
            api_messages = mock_create.call_args.kwargs["messages"]
            assert len(api_messages) == 1
            assert api_messages[0]["role"] == "system"
