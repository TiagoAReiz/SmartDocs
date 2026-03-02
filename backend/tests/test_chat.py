import pytest


@pytest.mark.asyncio
async def test_chat_without_auth(client):
    """Test chat without auth returns 401."""
    response = await client.post(
        "/chat",
        json={"question": "Quantos documentos tenho?"},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_chat_history_without_auth(client):
    """Test chat history without auth returns 401."""
    response = await client.get("/chat/threads/123e4567-e89b-12d3-a456-426614174000/messages")
    assert response.status_code == 401
