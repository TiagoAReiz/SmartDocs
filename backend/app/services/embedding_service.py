"""
Embedding service — generates vector embeddings via Azure OpenAI.

Uses the text-embedding-3-small model (1536 dimensions) by default.
Supports batching for efficient bulk embedding generation.
"""

from openai import AsyncAzureOpenAI
from loguru import logger

from app.config import settings


# Azure OpenAI allows up to 16 texts per embedding request
_BATCH_SIZE = 16


def _get_client() -> AsyncAzureOpenAI:
    """Create an Azure OpenAI async client."""
    return AsyncAzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT.strip(),
        api_key=settings.AZURE_OPENAI_KEY,
        api_version="2024-10-21",
    )


async def generate_embeddings(texts: list[str]) -> list[list[float]]:
    """Generate embeddings for a list of texts using Azure OpenAI.

    Processes in batches of up to 16 texts for efficiency.

    Args:
        texts: List of text strings to embed.

    Returns:
        List of embedding vectors (each a list of 1536 floats).

    Raises:
        RuntimeError: If Azure OpenAI is not configured.
    """
    if not (settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_KEY):
        raise RuntimeError("Azure OpenAI não configurado para embeddings")

    if not texts:
        return []

    client = _get_client()
    all_embeddings: list[list[float]] = []

    try:
        for i in range(0, len(texts), _BATCH_SIZE):
            batch = texts[i : i + _BATCH_SIZE]
            logger.debug(
                f"Gerando embeddings batch {i // _BATCH_SIZE + 1} "
                f"({len(batch)} textos)"
            )

            response = await client.embeddings.create(
                input=batch,
                model=settings.AZURE_OPENAI_EMBEDDING_DEPLOYMENT,
            )

            # Sort by index to maintain order
            sorted_data = sorted(response.data, key=lambda x: x.index)
            batch_embeddings = [item.embedding for item in sorted_data]
            all_embeddings.extend(batch_embeddings)

        logger.info(f"Embeddings gerados: {len(all_embeddings)} vetores")
        return all_embeddings

    finally:
        await client.close()


async def generate_single_embedding(text: str) -> list[float]:
    """Generate an embedding for a single text string.

    Convenience wrapper for query-time embedding generation.

    Args:
        text: The text to embed.

    Returns:
        Embedding vector (list of 1536 floats).
    """
    results = await generate_embeddings([text])
    return results[0]
