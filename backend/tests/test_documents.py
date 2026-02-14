import pytest


@pytest.mark.asyncio
async def test_list_documents_without_auth(client):
    """Test listing documents without auth returns 401."""
    response = await client.get("/documents")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_upload_without_auth(client):
    """Test upload without auth returns 401."""
    response = await client.post("/documents/upload")
    assert response.status_code == 401
