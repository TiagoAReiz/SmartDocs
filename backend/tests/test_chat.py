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
    response = await client.get("/chat/history")
    assert response.status_code == 401
